"""
FastAPI dependencies for authentication and role enforcement.

Three-stage check:

1. Extract bearer token from the Authorization header → 401 if missing/malformed.
2. Validate the JWT (signature, issuer, audience, expiry) → 401 on any failure.
3. Resolve the token's email against dev_hub.UserRoles → 403 if unknown.

By the time a route handler sees `AuthenticatedUser`, the caller has
been identified AND explicitly allow-listed at the correct tier. The
`require_admin` helper is a thin role check that layers on top.
"""
import logging

from fastapi          import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from api.auth._models     import AuthenticatedUser
from api.auth.verifier    import verify_token, TokenValidationError
from api.repositories     import UserRolesRepo


logger = logging.getLogger(__name__)


_bearer = HTTPBearer(auto_error=False)


def _extract_email(claims: dict) -> str:
    """Best-effort email extraction — AAD uses a couple different claim names."""

    for key in ("preferred_username", "upn", "email"):
        value = claims.get(key)
        if value:
            return value.strip().lower()

    raise HTTPException(
        status_code = status.HTTP_401_UNAUTHORIZED,
        detail      = "Token has no usable email claim",
    )


def _extract_display_name(claims: dict) -> str:
    """Prefer the Graph `name` claim, fall back to email."""

    return claims.get("name") or claims.get("preferred_username") or ""


async def get_current_user(
    request:     Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> AuthenticatedUser:
    """Resolve the caller. Raises 401 (unauthenticated) or 403 (unauthorized)."""

    if credentials is None:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = "Missing bearer token",
            headers     = {"WWW-Authenticate": "Bearer"},
        )

    try:
        claims = verify_token(credentials.credentials)
    except TokenValidationError as e:
        logger.info(f"Rejected token: {e}")
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail      = f"Invalid token: {e}",
            headers     = {"WWW-Authenticate": "Bearer"},
        ) from e

    email = _extract_email(claims)
    role  = UserRolesRepo.get_role(email)

    if role is None:
        logger.info(f"Denied access for unauthorized user: {email}")
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Your account is not authorized for DevHub. Contact an admin.",
        )

    return AuthenticatedUser(
        email        = email,
        display_name = _extract_display_name(claims),
        role         = role,
        claims       = claims,
    )


async def require_admin(
    user: AuthenticatedUser = Depends(get_current_user),
) -> AuthenticatedUser:
    """Admin-only gate. 403 if the caller's role isn't admin."""

    if user.role != "admin":
        raise HTTPException(
            status_code = status.HTTP_403_FORBIDDEN,
            detail      = "Admin role required for this action.",
        )

    return user
