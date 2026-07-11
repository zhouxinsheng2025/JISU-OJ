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

    # 判题引擎 — 并行判题 worker 数量
    JUDGE_WORKERS: int = 3
    JUDGE_POLL_INTERVAL: float = 0.5    # 轮询间隔(秒)
    COMPILE_TIME_LIMIT: int = 30
    SOURCE_SIZE_LIMIT: int = 256 * 1024
    OUTPUT_SIZE_LIMIT: int = 8 * 1024 * 1024

    # 目录
    DATA_DIR: str = "data/testcases"
    RUNS_DIR: str = "runs"

    # 计分板缓存 (秒)
    SCOREBOARD_CACHE_TTL: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
