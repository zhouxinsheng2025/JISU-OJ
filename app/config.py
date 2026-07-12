import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库 — SQLite 用于开发，PostgreSQL 用于生产
    DATABASE_URL: str = "sqlite+aiosqlite:///judge.db"
    # 生产示例: postgresql+asyncpg://user:pass@localhost:5432/judge

    # 连接池 (PostgreSQL 生效)
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 10

    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # 判题引擎 — 并行判题 worker 数量 (gunicorn 4进程 × 2 = 8总计)
    JUDGE_WORKERS: int = 2
    JUDGE_POLL_INTERVAL: float = 0.3  # 轮询间隔(秒)
    COMPILE_TIME_LIMIT: int = 30
    SOURCE_SIZE_LIMIT: int = 256 * 1024
    OUTPUT_SIZE_LIMIT: int = 8 * 1024 * 1024
    UPLOAD_SIZE_LIMIT: int = 8 * 1024 * 1024  # ZIP/CSV 上传限制 8MB

    # 目录
    DATA_DIR: str = "data/testcases"
    RUNS_DIR: str = "runs"

    # 计分板缓存 (秒)
    SCOREBOARD_CACHE_TTL: int = 5

    # 管理员默认凭据 (生产环境请通过 .env 修改)
    ADMIN_USERNAME: str = "chenjingbo"
    ADMIN_PASSWORD: str = "880730"

    # 运行模式 (生产环境已开启)
    PRODUCTION: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "server.log"

    # Docker 沙箱 (生产环境推荐开启)
    USE_DOCKER_SANDBOX: bool = False  # 启用 Docker 容器隔离执行

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
