import logging

from fastapi import APIRouter, FastAPI


logger = logging.getLogger(__name__)


def register_all_routes(app: FastAPI, routers: list[APIRouter]) -> None:
    """Mount every router in the ROUTES list onto the FastAPI app."""

    if not routers:
        logger.warning("No routers to register")

        return

    for r in routers:
        app.include_router(r)
        logger.info(f"Registered router tags={r.tags}")

    logger.info(f"Registered {len(routers)} routers")
