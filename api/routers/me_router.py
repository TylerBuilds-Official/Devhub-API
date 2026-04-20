"""
GET /me — who am I, and what tier am I?

Returned at the top of every SPA session so the frontend can hide
admin-only UI for viewers and show the signed-in user chip in the
header. The dependency layer has already validated the token and
resolved the role; this endpoint is a thin projection of that.
"""
from fastapi import APIRouter, Depends

from api._models.me_models import MeResponse
from api.auth              import AuthenticatedUser, get_current_user


router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeResponse)
async def me(user: AuthenticatedUser = Depends(get_current_user)) -> MeResponse:
    """Return the authenticated user's email, display name, and role."""

    return MeResponse(
        email        = user.email,
        display_name = user.display_name,
        role         = user.role,
    )
