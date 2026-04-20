"""
DevHub authentication layer.

Validates MSAL-issued JWTs from the shared JobScan Azure AD app
registration and gates every non-public route behind viewer/admin
RBAC backed by dev_hub.UserRoles.

Tokens are Microsoft Graph-audience — we only need identity, not
delegated API calls — so the audience check below pins to Graph's
well-known app ID rather than our own client ID.
"""
from api.auth._models      import AuthenticatedUser
from api.auth.dependencies import get_current_user, require_admin
from api.auth.verifier     import verify_token, TokenValidationError


__all__ = [
    "AuthenticatedUser",
    "get_current_user",
    "require_admin",
    "verify_token",
    "TokenValidationError",
]
