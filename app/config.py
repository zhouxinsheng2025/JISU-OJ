from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite+aiosqlite:///judge.db"
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24
    JUDGE_POLL_INTERVAL: int = 1  # 判题引擎轮询间隔(秒)
    COMPILE_TIME_LIMIT: int = 30  # 编译超时(秒)
    SOURCE_SIZE_LIMIT: int = 256 * 1024  # 源码大小限制
    OUTPUT_SIZE_LIMIT: int = 8 * 1024 * 1024  # 输出大小限制
    DATA_DIR: str = "data/testcases"
    RUNS_DIR: str = "runs"


settings = Settings()
