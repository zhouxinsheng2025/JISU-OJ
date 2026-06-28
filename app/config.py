import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///judge.db"
    # JWT
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    # 判题引擎
    JUDGE_POLL_INTERVAL: int = 1
    COMPILE_TIME_LIMIT: int = 30
    SOURCE_SIZE_LIMIT: int = 256 * 1024
    OUTPUT_SIZE_LIMIT: int = 8 * 1024 * 1024
    # 目录
    DATA_DIR: str = "data/testcases"
    RUNS_DIR: str = "runs"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
