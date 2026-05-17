import logging
import os
from typing import List
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from .engine import mcp, LOGGER
from . import tools, prompts

def _configure_runtime_logging() -> None:
    level_name = os.getenv("NRDS_LOG_LEVEL", "INFO").upper()
    level_value = getattr(logging, level_name, logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    # Configure this module logger explicitly so it always prints
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(level_value)
    stream_handler.setFormatter(formatter)

    LOGGER.handlers.clear()
    LOGGER.addHandler(stream_handler)
    LOGGER.setLevel(level_value)
    LOGGER.propagate = False

    # Optional: keep related loggers at the same level
    logging.getLogger("nextgen_plugins.chatbox.rest").setLevel(level_value)
    logging.getLogger("mcp").setLevel(level_value)
    logging.getLogger("mcp.server").setLevel(level_value)
    logging.getLogger("mcp.server.lowlevel.server").setLevel(level_value)

    LOGGER.info("Runtime logging configured with level=%s", level_name)

def _parse_allowed_origins() -> List[str]:
    """Read ALLOWED_ORIGINS from env (comma-separated). Defaults to wildcard.
    """
    raw = os.getenv("ALLOWED_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]

ALLOWED_ORIGINS = _parse_allowed_origins()

ALLOW_CREDENTIALS = ALLOWED_ORIGINS != ["*"]

CORS_MIDDLEWARE = [
    Middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=ALLOW_CREDENTIALS,
        allow_methods=["*"],
        allow_headers=["*"],
    ),
]

def main() -> None:
    _configure_runtime_logging()
    host = os.getenv("MCP_HOST", "0.0.0.0")
    port = int(os.getenv("MCP_PORT", "9003"))
    transport = "streamable-http"
    LOGGER.info("Starting DevCon2026 NRDS MCP on %s:%d with %s transport", host, port, transport)
    mcp.run(
        transport=transport,
        host=host,
        port=port,
        middleware=CORS_MIDDLEWARE,
    )