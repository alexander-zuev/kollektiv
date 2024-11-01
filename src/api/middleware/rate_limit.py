import time
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.routes import Routes
from src.utils.logger import get_logger

logger = get_logger()


class HealthCheckRateLimit(BaseHTTPMiddleware):
    """Rate limit for the health endpoint"""

    def __init__(self, app, requests_per_minute: int = 60, cleanup_interval: int = 300):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.requests = defaultdict(list)
        self.last_cleanup = time.time()
        self.cleanup_interval = cleanup_interval

    async def dispatch(self, request: Request, call_next):
        """Rate limit for the health endpoint"""
        if request.url.path == f"{Routes.System.HEALTH}":
            now = time.time()
            client_ip = request.client.host

            if now - self.last_cleanup > self.cleanup_interval:
                self._cleanup_old_data(now)
                self.last_cleanup = now

            self.requests[client_ip] = [req_time for req_time in self.requests[client_ip] if req_time > now - 60]

            if len(self.requests[client_ip]) >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for IP {client_ip} on health endpoint")
                return Response(
                    "Rate limit exceeded",
                    status_code=429,
                    headers={
                        "Retry-After": "60",
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(now + 60)),
                    },
                )

            self.requests[client_ip].append(now)

            response = await call_next(request)
            remaining = self.requests_per_minute - len(self.requests[client_ip])
            response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
            response.headers["X-RateLimit-Remaining"] = str(remaining)
            response.headers["X-RateLimit-Reset"] = str(int(now + 60))
            return response

        return await call_next(request)

    def _cleanup_old_data(self, now: float):
        """Remove IPs that haven't made requests in the last minute"""
        for ip in list(self.requests.keys()):
            if not any(t > now - 60 for t in self.requests[ip]):
                del self.requests[ip]
