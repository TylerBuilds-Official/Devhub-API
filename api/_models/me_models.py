"""
Pydantic model for GET /me.

The SPA fetches this once after sign-in to know the caller's identity
and role, then decides which admin-only UI to render.
"""
from pydantic import BaseModel

from api._dataclasses.user_role import Role


class MeResponse(BaseModel):
    """Identity + role for the currently authenticated user."""

    email:        str
    display_name: str
    role:         Role
