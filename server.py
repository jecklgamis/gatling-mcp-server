from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from server.gatling_tools import gatling_tools, mcp

gatling_mcp_app = mcp.http_app(path="/")


@asynccontextmanager
async def lifespan(app):
    async with gatling_mcp_app.lifespan(app):
        yield


app = FastAPI(
    title="Gatling MCP Server",
    description="MCP server for submitting and monitoring Gatling load tests via gatling-server",
    version="0.1.0",
    lifespan=lifespan,
)


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
    app.get(f"/{tool_fn.__name__.lstrip('_')}", tags=["gatling"])(tool_fn)

app.mount("/gatling_mcp", gatling_mcp_app)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=58090)
