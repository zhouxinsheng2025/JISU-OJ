"""
中央日志配置 — 替代散落的 print() 调用
"""
import logging
import sys
from app.config import settings


def configure_logging() -> None:
    """配置根日志器，在 startup 时调用一次。"""
    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root = logging.getLogger()
    root.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))

    # 清除已有 handler（避免重复添加，如 uvicorn 已配置的）
    root.handlers.clear()

    # 控制台 handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # 文件 handler（仅当配置了 LOG_FILE）
    if settings.LOG_FILE:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            settings.LOG_FILE, maxBytes=10 * 1024 * 1024, backupCount=5
        )
        file_handler.setFormatter(fmt)
        root.addHandler(file_handler)

    # 抑制过于冗长的第三方日志
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
