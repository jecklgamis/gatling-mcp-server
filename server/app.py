import hmac
import logging
import os
from contextlib import asynccontextmanager
from importlib.metadata import PackageNotFoundError, version

import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from server.gatling_tools import gatling_tools, mcp

try:
    __version__ = version("gatling-mcp-server")
except PackageNotFoundError:
    __version__ = "0.0.0-dev"

logger = logging.getLogger("gatling_mcp_server")

GATLING_MCP_API_TOKEN = os.environ.get("GATLING_MCP_API_TOKEN", "default")
_EXPECTED_AUTH_HEADER = f"Bearer {GATLING_MCP_API_TOKEN}".encode()
if GATLING_MCP_API_TOKEN == "default":
    logger.warning(
        "GATLING_MCP_API_TOKEN is unset - using the insecure default token. "
        "Set GATLING_MCP_API_TOKEN before exposing this server beyond localhost."
    )

# Tools that only read state; everything else mutates gatling-server (submits/aborts
# a task, or uploads a file) and is exposed via POST instead of GET so it can't be
# triggered by a bare link/image tag and doesn't get cached/logged with parameters
# in the URL.
_READ_ONLY_TOOLS = {"get_task_status", "get_console_log", "get_simulation_log"}

# Unauthenticated so k8s (or any other) liveness/readiness probe can hit it
# without a token.
_PUBLIC_PATHS = {"/healthz"}

gatling_mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app):
    async with gatling_mcp_app.lifespan(app):
        yield


app = FastAPI(
    title="Gatling MCP Server",
    description="MCP server for submitting and monitoring Gatling load tests via gatling-server",
    version=__version__,
    lifespan=lifespan,
)


class BearerAuthMiddleware:
    """Plain ASGI middleware (not BaseHTTPMiddleware) so it doesn't buffer the
    mounted MCP app's streamable-http responses."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["path"] in _PUBLIC_PATHS:
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        auth = headers.get(b"authorization", b"")
        if not hmac.compare_digest(auth, _EXPECTED_AUTH_HEADER):
            response = JSONResponse({"error": "unauthorized"}, status_code=401)
            return await response(scope, receive, send)
        return await self.app(scope, receive, send)


app.add_middleware(BearerAuthMiddleware)


@app.get("/healthz")
async def healthz():
    """Unauthenticated liveness/readiness probe target."""
    return {"status": "ok"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "app_name": "gatling-mcp-server",
        "message": "It works on my machine!",
        "endpoints": {
            "docs": "/docs",
            "gatling_mcp": "/gatling_mcp",
        },
    }


# FastAPI routes
for tool_fn in gatling_tools:
    tool_name = tool_fn.__name__.lstrip("_")
    method = app.get if tool_name in _READ_ONLY_TOOLS else app.post
    method(f"/{tool_name}", tags=["gatling"])(tool_fn)

app.mount("/gatling_mcp", gatling_mcp_app)


def main():
    uvicorn.run(app, host="0.0.0.0", port=58090, ws="websockets-sansio")


if __name__ == "__main__":
    main()
