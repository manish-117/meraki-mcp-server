import time
import json
import logging
import logging.handlers
from pathlib import Path

LOG_DIR = Path("/var/log/meraki-mcp")
LOG_DIR.mkdir(parents=True, exist_ok=True)

_logger = logging.getLogger("meraki.audit")
_logger.setLevel(logging.INFO)
_logger.propagate = False
_handler = logging.handlers.RotatingFileHandler(
    LOG_DIR / "audit.log", maxBytes=50 * 1024 * 1024, backupCount=10
)
_handler.setFormatter(logging.Formatter("%(message)s"))
_logger.addHandler(_handler)

class AuditLoggerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        method = scope.get("method", "")
        path = scope.get("path", "")
        client = scope.get("client", ("unknown", 0))[0]

        status_holder = []

        async def send_wrapper(message):
            if message["type"] == "http.response.start":
                status_holder.append(message["status"])
            await send(message)

        await self.app(scope, receive, send_wrapper)

        duration_ms = round((time.monotonic() - start) * 1000, 2)
        status = status_holder[0] if status_holder else 0

        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "client": client,
            "method": method,
            "path": path,
            "status": status,
            "duration_ms": duration_ms,
        }
        _logger.info(json.dumps(entry))
