import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding window rate limiter per client IP."""

    def __init__(
        self, app: Any, auth_limit: int = 10, api_limit: int = 60, chat_limit: int = 30
    ) -> None:
        super().__init__(app)
        self._auth_limit = auth_limit
        self._api_limit = api_limit
        self._chat_limit = chat_limit
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "unknown"

    def _get_limit(self, path: str) -> int:
        if "/auth/" in path:
            return self._auth_limit
        if "/conversations/" in path and ("send" in path or "messages" in path):
            return self._chat_limit
        return self._api_limit

    def _is_rate_limited(self, client_ip: str, path: str) -> tuple[bool, int]:
        limit = self._get_limit(path)
        now = time.time()
        window = 60.0  # 1 minute sliding window

        # Clean old entries
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if now - t < window
        ]

        if len(self._requests[client_ip]) >= limit:
            oldest = self._requests[client_ip][0]
            retry_after = int(window - (now - oldest)) + 1
            return True, retry_after

        self._requests[client_ip].append(now)
        return False, 0

    async def dispatch(self, request: Request, call_next: Callable) -> Any:  # type: ignore[type-arg]
        # Skip rate limiting for health checks
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        limited, retry_after = self._is_rate_limited(client_ip, request.url.path)

        if limited:
            return JSONResponse(
                status_code=429,
                content={
                    "type": "https://knowledge-os.local/problems/rate-limit-exceeded",
                    "title": "Rate Limit Exceeded",
                    "status": 429,
                    "detail": f"Too many requests. Retry after {retry_after} seconds.",
                    "error_code": "rate_limit_exceeded",
                    "instance": str(request.url.path),
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)
