"""
GET    /users           — list all entries in dev_hub.UserRoles (admin only).
POST   /users           — add a new user (admin only).
PATCH  /users/{email}   — update role/notes on an existing user (admin only).
DELETE /users/{email}   — remove a user from the allowlist (admin only).

Self-operation guards: an admin can't demote themselves to viewer and
can't delete themselves. Both would create a last-admin lockout foot-
gun. If the last admin really wants out, they can promote a second
admin first, or edit the table directly via SQL.
"""
from fastapi import APIRouter, Depends, HTTPException

from api._models      import (
    CreateUserRequest, UpdateUserRequest,
    UserRoleInfo, UserRolesResponse,
)
from api.auth         import AuthenticatedUser, require_admin
from api.repositories import UserRolesRepo


router = APIRouter(tags=["users"])


def _to_info(record) -> UserRoleInfo:
    return UserRoleInfo(
        email      = record.email,
        role       = record.role,
        created_at = record.created_at,
        created_by = record.created_by,
        notes      = record.notes,
    )


@router.get("/users", response_model=UserRolesResponse)
async def list_users(_: AuthenticatedUser = Depends(require_admin)) -> UserRolesResponse:
    """Return every allowlisted user with their role and creation metadata."""

    records = UserRolesRepo.list_all()
    return UserRolesResponse(users=[_to_info(r) for r in records])


@router.post("/users", response_model=UserRoleInfo, status_code=201)
async def create_user(
        payload: CreateUserRequest,
        admin:   AuthenticatedUser = Depends(require_admin) ) -> UserRoleInfo:
    """Add a new user to the allowlist."""

    email = payload.email.strip().lower()

    if UserRolesRepo.get_role(email) is not None:
        raise HTTPException(
            status_code = 409,
            detail      = f"User {email} already exists. Use PATCH to update their role.",
        )

    UserRolesRepo.upsert(
        email      = email,
        role       = payload.role,
        created_by = admin.email,
        notes      = payload.notes,
    )

    record = UserRolesRepo.get(email)
    if record is None:
        raise HTTPException(status_code=500, detail="User write did not persist")

    return _to_info(record)


@router.patch("/users/{email}", response_model=UserRoleInfo)
async def update_user(
        email:   str,
        payload: UpdateUserRequest,
        admin:   AuthenticatedUser = Depends(require_admin) ) -> UserRoleInfo:
    """Change a user's role and/or notes."""

    email = email.strip().lower()
    existing = UserRolesRepo.get(email)

    if existing is None:
        raise HTTPException(status_code=404, detail=f"Unknown user: {email}")

    new_role  = payload.role  if payload.role  is not None else existing.role
    new_notes = payload.notes if payload.notes is not None else existing.notes

    # Self-guard: the last admin can't demote themselves.
    if email == admin.email and new_role != 'admin':
        raise HTTPException(
            status_code = 400,
            detail      = "You can't demote yourself. Promote another admin first.",
        )

    UserRolesRepo.upsert(email=email, role=new_role, notes=new_notes)

    updated = UserRolesRepo.get(email)
    if updated is None:
        raise HTTPException(status_code=500, detail="User update did not persist")

    return _to_info(updated)


@router.delete("/users/{email}", status_code=204)
async def delete_user(
        email: str,
        admin: AuthenticatedUser = Depends(require_admin) ) -> None:
    """Remove a user from the allowlist."""

    email = email.strip().lower()

    if email == admin.email:
        raise HTTPException(
            status_code = 400,
            detail      = "You can't delete yourself. Ask another admin to remove you.",
        )

    deleted = UserRolesRepo.delete(email)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Unknown user: {email}")
