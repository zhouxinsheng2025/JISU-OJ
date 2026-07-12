from fastapi import Request, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.services.auth_service import decode_token
from app.models import User, UserRole
from sqlalchemy import select


async def get_current_user_from_cookie(request: Request, db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("access_token")
    if token is None:
        return None
    payload = decode_token(token)
    if payload is None:
        return None
    try:
        user_id = int(payload["sub"])
    except (ValueError, KeyError):
        return None
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


def require_role(role: str):
    async def dependency(request: Request, db: AsyncSession = Depends(get_db)):
        user = await get_current_user_from_cookie(request, db)
        if user is None:
            return RedirectResponse(url="/auth/login", status_code=303)
        if not user.enabled:
            return RedirectResponse(url="/auth/login", status_code=303)
        if user.role.value != role:
            return RedirectResponse(url="/auth/login", status_code=303)
        return user
    return dependency
