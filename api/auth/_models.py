"""
Authenticated-user model.

Assembled by the dependency layer after a token has been validated AND
the user's role has been resolved from dev_hub.UserRoles. A request
that reaches a route handler with an AuthenticatedUser in scope is,
by construction, authorized — unknown users are 403'd before the
handler ever runs.
"""
from dataclasses import dataclass
from typing import Any

from api._dataclasses.user_role import Role


@dataclass(frozen=True)
class AuthenticatedUser:
    """A signed-in, role-resolved user."""

    email:        str
    display_name: str
    role:         Role
    claims:       dict[str, Any]   # raw decoded JWT claims — for audit/debug
