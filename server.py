"""
Entry point for Meraki MCP Server with auth, rate limiting, and audit logging.
Run with: uvicorn server:app --host 127.0.0.1 --port 8000
"""
import importlib.util
import sys
from dotenv import load_dotenv

load_dotenv()

# Load meraki-mcp-dynamic.py (hyphen in filename makes it not directly importable)
spec = importlib.util.spec_from_file_location("meraki_mcp_dynamic", "meraki-mcp-dynamic.py")
module = importlib.util.module_from_spec(spec)
sys.modules["meraki_mcp_dynamic"] = module
spec.loader.exec_module(module)

mcp = module.mcp

# Middleware stack (outermost to innermost): Auth → RateLimit → AuditLog → FastMCP
from middleware.auth import BearerAuthMiddleware
from middleware.rate_limiter import RateLimiterMiddleware
from middleware.audit_logger import AuditLoggerMiddleware

app = mcp.streamable_http_app()
app = AuditLoggerMiddleware(app)
app = RateLimiterMiddleware(app, rate=5.0, burst=30)
app = BearerAuthMiddleware(app)
