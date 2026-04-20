"""
GET /upstream/apps — proxy to UpdateSuiteAPI's /apps endpoint.

Single-origin pattern — the frontend talks only to DevHub so there's
one base URL, one CORS config, one future auth story. DevHub forwards
to UpdateSuite when the data lives there.
"""
from fastapi import APIRouter, Depends, HTTPException, Request

from api.auth import get_current_user


router = APIRouter(tags=["upstream"], dependencies=[Depends(get_current_user)])


@router.get("/upstream/apps")
async def list_upstream_apps(request: Request) -> dict:
    """Return UpdateSuite's /apps registry — proxied verbatim."""

    client = request.app.state.updatesuite

    try:
        return await client.list_apps()

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UpdateSuite upstream error: {e}") from e
