"""
简易内存限流中间件 — 无需额外依赖

使用滑动窗口计数，每小时自动清理过期条目。
"""
import time
from collections import defaultdict
from fastapi import Request
from fastapi.responses import JSONResponse


class RateLimiter:
    """基于 IP 的滑动窗口限流器。"""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._cleanup_at = time.time() + 3600  # 每小时清理一次

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        self._maybe_cleanup(now)
        window = [t for t in self._store[key] if now - t < self.window_seconds]
        self._store[key] = window
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True

    def _maybe_cleanup(self, now: float) -> None:
        if now < self._cleanup_at:
            return
        # 清理所有过期条目
        for key in list(self._store.keys()):
            self._store[key] = [t for t in self._store[key] if now - t < self.window_seconds]
            if not self._store[key]:
                del self._store[key]
        self._cleanup_at = now + 3600


# 全局限流器实例
_login_limiter = RateLimiter(max_requests=10, window_seconds=60)   # 10次/分钟
_submit_limiter = RateLimiter(max_requests=30, window_seconds=60)  # 30次/分钟


async def rate_limit_middleware(request: Request, call_next):
    """FastAPI 中间件：对登录和提交接口限流。"""
    path = request.url.path

    if path in ("/auth/login", "/team/submit") and request.method == "POST":
        client_ip = request.client.host if request.client else "127.0.0.1"
        limiter = _login_limiter if path == "/auth/login" else _submit_limiter

        if not limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "请求过于频繁，请稍后再试 (Too Many Requests)"},
            )

    response = await call_next(request)
    return response
