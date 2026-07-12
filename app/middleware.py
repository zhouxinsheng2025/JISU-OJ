"""
简易内存限流中间件 — 纯 ASGI 实现，兼容 async SQLAlchemy

使用滑动窗口计数，每小时自动清理过期条目。
"""
import time
from collections import defaultdict
from starlette.types import ASGIApp, Scope, Receive, Send
from starlette.responses import JSONResponse


class RateLimiter:
    """基于 IP 的滑动窗口限流器。"""

    def __init__(self, max_requests: int, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store: dict[str, list[float]] = defaultdict(list)
        self._cleanup_at = time.time() + 3600

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
        for key in list(self._store.keys()):
            self._store[key] = [t for t in self._store[key] if now - t < self.window_seconds]
            if not self._store[key]:
                del self._store[key]
        self._cleanup_at = now + 3600


_login_limiter = RateLimiter(max_requests=10, window_seconds=60)
_submit_limiter = RateLimiter(max_requests=30, window_seconds=60)


class RateLimitMiddleware:
    """纯 ASGI 中间件 — 避免 BaseHTTPMiddleware 的 greenlet 兼容问题。"""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        method = scope.get("method", "")

        if path in ("/auth/login", "/team/submit") and method == "POST":
            # 获取客户端 IP
            client = scope.get("client")
            client_ip = client[0] if client else "127.0.0.1"
            limiter = _login_limiter if path == "/auth/login" else _submit_limiter

            if not limiter.is_allowed(client_ip):
                response = JSONResponse(
                    status_code=429,
                    content={"detail": "请求过于频繁，请稍后再试 (Too Many Requests)"},
                )
                await response(scope, receive, send)
                return

        await self.app(scope, receive, send)


# 导出的工厂函数，兼容 FastAPI add_middleware
def rate_limit_middleware(app: ASGIApp) -> RateLimitMiddleware:
    return RateLimitMiddleware(app)
