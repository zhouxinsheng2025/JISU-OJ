import asyncio, os, secrets, logging
from fastapi import FastAPI, WebSocket
from fastapi.responses import RedirectResponse, FileResponse
from app.config import settings
from app.judge.engine import start_judge_engine
from app.logging_config import configure_logging
from app.middleware import RateLimitMiddleware

logger = logging.getLogger(__name__)

app = FastAPI(
    title="JISU程序设计裁判系统",
    docs_url="/docs" if not settings.PRODUCTION else None,
    redoc_url="/redoc" if not settings.PRODUCTION else None,
)

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


@app.get("/static/{filename:path}")
async def static_file(filename: str):
    # 防路径遍历：规范化路径后校验仍在 STATIC_DIR 内
    safe_path = os.path.realpath(os.path.join(STATIC_DIR, filename))
    if not safe_path.startswith(os.path.realpath(STATIC_DIR) + os.sep) \
       and safe_path != os.path.realpath(STATIC_DIR):
        from fastapi.responses import PlainTextResponse
        return PlainTextResponse("Not Found", status_code=404)
    return FileResponse(safe_path)


@app.on_event("startup")
async def startup():
    configure_logging()
    os.makedirs(settings.RUNS_DIR, exist_ok=True)
    os.makedirs(settings.DATA_DIR, exist_ok=True)
    from app.database import init_db
    await init_db()
    await _seed_admin()
    await _seed_practice_contest()
    # Docker 沙箱模式：确保镜像已构建
    if settings.USE_DOCKER_SANDBOX:
        from app.judge.sandbox import build_sandbox_image
        _ = await asyncio.to_thread(build_sandbox_image)
    await start_judge_engine()


async def _seed_admin():
    from app.database import async_session
    from app.models import User, UserRole
    from app.services.auth_service import hash_password
    async with async_session() as db:
        from sqlalchemy import select
        username = settings.ADMIN_USERNAME
        password = settings.ADMIN_PASSWORD
        # 如果未配置密码，自动生成一个并打印到控制台（仅首次）
        if not password:
            password = secrets.token_urlsafe(12)
            logger.warning("=" * 55)
            logger.warning("  未配置 ADMIN_PASSWORD，已自动生成管理员密码")
            logger.warning(f"  用户名: {username}")
            logger.warning(f"  密码:   {password}")
            logger.warning("  请通过 .env 的 ADMIN_PASSWORD 设置自定义密码")
            logger.warning("=" * 55)

        result = await db.execute(select(User).where(User.username == username))
        if result.scalar_one_or_none() is None:
            admin = User(
                username=username,
                password_hash=hash_password(password),
                teamname="Administrator",
                role=UserRole.JURY,
            )
            db.add(admin)
            try:
                await db.commit()
                logger.info("管理员账号已创建 (username=%s)", username)
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
            logger.info("开放练习比赛已创建")


# 注册路由
from app.routers import auth, jury, team, public
app.include_router(auth.router)
app.include_router(jury.router)
app.include_router(team.router)
app.include_router(public.router)


@app.get("/")
async def root():
    return RedirectResponse(url="/auth/login")


@app.get("/health")
async def health_check():
    """健康检查端点 — 供负载均衡器探测。"""
    try:
        from app.database import async_session
        from sqlalchemy import text
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": str(e)}


@app.websocket("/ws/judge-updates")
async def judge_websocket(websocket):
    """WebSocket 端点 — 判题完成后实时推送结果。"""
    from fastapi import WebSocketDisconnect
    from app.judge.engine import subscribe, unsubscribe

    await websocket.accept()
    queue = subscribe()
    try:
        while True:
            event = await queue.get()
            await websocket.send_json(event)
    except (WebSocketDisconnect, Exception):
        unsubscribe(queue)


# 在路由全部注册后，外层包装限流中间件（不影响 WebSocket）
app.middleware_stack = RateLimitMiddleware(app.middleware_stack)
