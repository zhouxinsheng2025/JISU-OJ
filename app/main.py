import asyncio, os
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, FileResponse
from app.config import settings
from app.judge.engine import start_judge_engine

app = FastAPI(title="JISU程序设计裁判系统")

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/static/{filename}")
async def static_file(filename: str):
    return FileResponse(os.path.join(STATIC_DIR, filename))


@app.on_event("startup")
async def startup():
    os.makedirs(settings.RUNS_DIR, exist_ok=True)
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    from app.database import init_db
    await init_db()
    await _seed_admin()
    await _seed_practice_contest()
    await start_judge_engine()


async def _seed_admin():
    from app.database import async_session
    from app.models import User, UserRole
    from app.services.auth_service import hash_password
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.username == "chenjingbo"))
        if result.scalar_one_or_none() is None:
            admin = User(
                username="chenjingbo",
                password_hash=hash_password("880730"),
                teamname="Administrator",
                role=UserRole.JURY,
            )
            db.add(admin)
            try:
                await db.commit()
            except Exception:
                await db.rollback()  # 多worker竞争，已被其他worker创建


async def _seed_practice_contest():
    """Seed the 开放练习 practice contest if it doesn't exist."""
    from datetime import datetime
    from app.database import async_session
    from app.models import Contest, ContestType
    async with async_session() as db:
        from sqlalchemy import select
        result = await db.execute(
            select(Contest).where(Contest.ctype == ContestType.PRACTICE).limit(1)
        )
        if result.scalar_one_or_none() is None:
            practice = Contest(
                title="开放练习",
                start_time=datetime(2000, 1, 1),
                end_time=datetime(2099, 12, 31),
                score_mode="icpc",
                ctype=ContestType.PRACTICE,
                enabled=True,
            )
            db.add(practice)
            try:
                await db.commit()
            except Exception:
                await db.rollback()
            print("[Seed] 开放练习比赛已创建")


# 注册路由
from app.routers import auth, jury, team, public
app.include_router(auth.router)
app.include_router(jury.router)
app.include_router(team.router)
app.include_router(public.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")
