"""
FastAPI app factory.

Pure construction — no side effects beyond instantiating and configuring
the FastAPI instance. Called by api.main and importable by tests.
"""
from fastapi import FastAPI

from api.build.cors            import attach_cors
from api.build.lifespan        import lifespan
from api.routers.register_all  import register_all_routes
from api.routers.routes        import ROUTES


def build_api() -> FastAPI:
    """Construct and return the configured FastAPI application."""

    app = FastAPI(
        title       = "DevHub API",
        description = "Backend for the DevHub MFC dev console. Orchestrates health, deploys, and docs across MFC projects.",
        version     = "0.1.0",
        lifespan    = lifespan,
    )

    attach_cors(app)
    register_all_routes(app, ROUTES)

    return app
