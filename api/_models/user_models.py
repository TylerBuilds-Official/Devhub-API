"""
Pydantic models for the /users admin endpoints.
"""
from datetime import datetime

from pydantic import BaseModel, Field

from api._dataclasses.user_role import Role


class UserRoleInfo(BaseModel):
    email:       str
    role:        Role
    created_at:  datetime
    created_by:  str | None = None
    notes:       str | None = None


class UserRolesResponse(BaseModel):
    users: list[UserRoleInfo]


class CreateUserRequest(BaseModel):
    email: str = Field(min_length=3, max_length=256)
    role:  Role
    notes: str | None = Field(default=None, max_length=512)


class UpdateUserRequest(BaseModel):
    role:  Role | None       = None
    notes: str | None        = Field(default=None, max_length=512)
