import os
import json

BEARER_TOKEN = os.getenv("MCP_BEARER_TOKEN", "")
EXCLUDED_PATHS = {"/health", "/healthz"}

class BearerAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode()

        if not BEARER_TOKEN:
            await _send_json(send, 500, {"error": "Server misconfigured: MCP_BEARER_TOKEN not set"})
            return

        if not auth.startswith("Bearer ") or auth[7:] != BEARER_TOKEN:
            await _send_json(send, 401, {"error": "Unauthorized: valid Bearer token required"})
            return

        await self.app(scope, receive, send)

async def _send_json(send, status: int, body: dict):
    content = json.dumps(body).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(content)).encode()),
        ],
    })
    await send({"type": "http.response.body", "body": content})
