import asyncio, os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, FileResponse
from app.config import settings
from app.judge.engine import judge_loop

app = FastAPI(title="JISU程序设计裁判系统")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@app.get("/static/{filename}")
async def static_file(filename: str):
    return FileResponse(os.path.join(STATIC_DIR, filename))


@app.on_event("startup")
async def startup():
    # 确保必要目录存在
    os.makedirs(settings.RUNS_DIR, exist_ok=True)
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    from app.database import init_db
    await init_db()
    await _seed_admin()
    asyncio.create_task(judge_loop())


async def _seed_admin():
    from app.database import async_session
    from app.models import User, UserRole
    from app.services.auth_service import hash_password
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "admin"))
        if result.scalar_one_or_none() is None:
            admin = User(
                username="admin",
                password_hash=hash_password("admin"),
                teamname="Administrator",
                role=UserRole.JURY,
            )
            db.add(admin)
            await db.commit()


# 注册路由
from app.routers import auth, jury, team, public
app.include_router(auth.router)
app.include_router(jury.router)
app.include_router(team.router)
app.include_router(public.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")
