from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

import logging

LOGGER = logging.getLogger("devcon_mcp")

mcp = FastMCP("DevCon2026 NRDS MCP")

@mcp.custom_route("/health", methods=["GET"])
async def health_check(_request: Request) -> JSONResponse:
    """Liveness probe used by Docker HEALTHCHECK and container orchestrators.
    Returns 200 with a minimal payload. Does not exercise downstream
    dependencies (S3, etc.) - keep it cheap so polling stays free.
    """
    return JSONResponse({"status": "ok"})