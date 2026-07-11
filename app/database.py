from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings
from app.models import Base

# 连接池配置 — PostgreSQL 使用连接池，SQLite 单连接
_connect_args = {}
if "sqlite" in settings.DATABASE_URL:
    _connect_args["check_same_thread"] = False

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    pool_size=settings.DB_POOL_SIZE if "postgresql" in settings.DATABASE_URL else 1,
    max_overflow=settings.DB_MAX_OVERFLOW if "postgresql" in settings.DATABASE_URL else 0,
    connect_args=_connect_args,
    # SQLite WAL 模式提升并发读
    **({"pool_pre_ping": True} if "postgresql" in settings.DATABASE_URL else {})
)

async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db():
    async with engine.begin() as conn:
        # 优先使用 Alembic 迁移；失败时回退到 create_all
        try:
            from alembic.config import Config as AlembicConfig
            from alembic import command
            import os
            alembic_cfg = AlembicConfig(
                os.path.join(os.path.dirname(__file__), "..", "alembic.ini")
            )
            # 覆盖 alembic.ini 中的 URL（使用 app 配置的值）
            alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
            # 在连接上运行迁移
            await conn.run_sync(lambda sync_conn: command.upgrade(alembic_cfg, "head"))
        except Exception:
            # 回退: 直接建表（适用于首次运行或 Alembic 不可用时）
            await conn.run_sync(Base.metadata.create_all)

        # SQLite: 开启 WAL 模式提升读并发
        if "sqlite" in settings.DATABASE_URL:
            await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            await conn.exec_driver_sql("PRAGMA busy_timeout=5000")
            await conn.exec_driver_sql("PRAGMA synchronous=NORMAL")


async def get_db():
    async with async_session() as session:
        yield session


def is_postgresql() -> bool:
    return "postgresql" in settings.DATABASE_URL
