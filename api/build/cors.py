"""
CORS configuration.

Locked to an explicit origin list since auth is in place — wide-open
CORS alongside bearer tokens is a footgun waiting to happen. Origins
come from DEVHUB_ALLOWED_ORIGINS (comma-separated), default covers
local Vite dev.
"""
import os

from fastapi                    import FastAPI
from fastapi.middleware.cors    import CORSMiddleware


def _parse_origins() -> list[str]:
    raw = os.getenv("DEVHUB_ALLOWED_ORIGINS", "http://localhost:5174")
    return [o.strip() for o in raw.split(",") if o.strip()]


def attach_cors(app: FastAPI) -> None:
    """Mount the CORS middleware, scoped to the configured origins."""

    app.add_middleware(
        CORSMiddleware,
        allow_origins     = _parse_origins(),
        allow_credentials = True,
        allow_methods     = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers     = ["Authorization", "Content-Type"],
    )
