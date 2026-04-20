"""
User role loaded from dev_hub.UserRoles.

The source of truth for who is allowed into DevHub and at what tier.
Email is lowercased on read/write so token-claim lookups are case-
insensitive.

Role is a two-tier string — 'viewer' (read-only) or 'admin' (can deploy).
Enforced by a CHECK constraint at the DB level.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal


Role = Literal["viewer", "admin"]


@dataclass(frozen=True)
class UserRole:
    """A single row from dev_hub.UserRoles."""

    email:       str
    role:        Role
    created_at:  datetime
    created_by:  str | None = None
    notes:       str | None = None
