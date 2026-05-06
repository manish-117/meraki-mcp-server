import time
import asyncio
import json

class TokenBucket:
    def __init__(self, rate: float, burst: int):
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> tuple[bool, float]:
        async with self._lock:
            now = time.monotonic()
            self.tokens = min(self.burst, self.tokens + (now - self.last) * self.rate)
            self.last = now
            if self.tokens >= 1:
                self.tokens -= 1
                return True, 0.0
            wait = (1 - self.tokens) / self.rate
            return False, round(wait, 2)

class RateLimiterMiddleware:
    def __init__(self, app, rate: float = 5.0, burst: int = 30):
        self.app = app
        self.bucket = TokenBucket(rate, burst)

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in ("/health", "/healthz"):
            await self.app(scope, receive, send)
            return

        allowed, retry_after = await self.bucket.acquire()
        if not allowed:
            content = json.dumps({"error": "Rate limit exceeded", "retry_after_seconds": retry_after}).encode()
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(content)).encode()),
                    (b"retry-after", str(retry_after).encode()),
                ],
            })
            await send({"type": "http.response.body", "body": content})
            return

        await self.app(scope, receive, send)
