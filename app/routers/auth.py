import os
from fastapi import APIRouter, Request, Form, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models import User
from app.services.auth_service import verify_password, create_token
from app.templates_helpers import templates

router = APIRouter(prefix="/auth", tags=["auth"])

TEMPLATE_DIR = "auth"


@router.get("/login")
async def login_page(request: Request):
    photo_dir = os.path.join(os.path.dirname(__file__), "..", "static", "photos")
    photos = []
    if os.path.isdir(photo_dir):
        exts = {".jpg", ".jpeg", ".png", ".webp"}
        photos = [f for f in os.listdir(photo_dir) if os.path.splitext(f)[1].lower() in exts]
    return templates.TemplateResponse(
        f"{TEMPLATE_DIR}/login.html",
        {"request": request, "photos": photos}
    )


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/login.html",
            {"request": request, "error": "用户名或密码错误", "photos": []},
            status_code=401,
        )

    if not user.enabled:
        return templates.TemplateResponse(
            f"{TEMPLATE_DIR}/login.html",
            {"request": request, "error": "账号已被禁用", "photos": []},
            status_code=403,
        )

    token = create_token(user.id, user.role.value)
    redirect_url = "/jury/" if user.role.value == "jury" else "/team/"

    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=303)
    response.delete_cookie("access_token")
    return response
