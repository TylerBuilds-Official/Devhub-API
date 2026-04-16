"""
GET /health — liveness check. No auth, no dependencies, no DB.
"""
from fastapi import APIRouter


router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Returns ok if the API process is up."""

    return {"status": "ok"}
