"""
JWT verifier for AAD-issued ID tokens.

We validate ID tokens — not Graph access tokens — because Graph access
tokens use a hashed-nonce signing scheme that standard JWT libraries
can't verify (Microsoft explicitly documents that Graph access tokens
"should not be inspected by the service for which they were issued").
ID tokens from the same sign-in flow are standard RS256 JWTs signed
with the tenant's published JWKS and carry the same identity claims
(`preferred_username`, `upn`, `name`) we need for RBAC lookup.

Validates:
- Signature (RS256 only) against the tenant's JWKS
- Issuer is our tenant — accepts both v1 (`sts.windows.net`) and v2
  (`login.microsoftonline.com/.../v2.0`) issuer formats
- Audience is our app registration's client id (ID tokens have
  aud = client_id)
- `exp` / `nbf` with 60s clock skew leeway

Rejects anything missing a `kid`, using `alg: none`, or from a different
tenant. Raises TokenValidationError on any failure — the dependency
layer translates that to a 401.
"""
import logging
import os
from typing import Any

import jwt
from jwt.algorithms import RSAAlgorithm

from api.auth import jwks


logger = logging.getLogger(__name__)


class TokenValidationError(Exception):
    """Raised when a presented JWT fails any validation step."""


def _expected_issuers() -> list[str]:
    tenant = os.environ["AAD_TENANT_ID"]
    return [
        f"https://login.microsoftonline.com/{tenant}/v2.0",
        f"https://sts.windows.net/{tenant}/",
    ]


def _public_key_for(token: str):
    """Pluck the `kid` from the token header and resolve to an RSA public key."""

    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as e:
        raise TokenValidationError(f"Malformed token header: {e}") from e

    kid = header.get("kid")
    if not kid:
        raise TokenValidationError("Token header missing `kid`")

    if header.get("alg") != "RS256":
        raise TokenValidationError(f"Unexpected signing algorithm: {header.get('alg')}")

    jwk = jwks.get_key(kid)
    if jwk is None:
        # Key may have rotated since we cached — refresh once and retry.
        jwks.invalidate()
        jwk = jwks.get_key(kid)

    if jwk is None:
        raise TokenValidationError(f"No JWKS key matches kid={kid}")

    return RSAAlgorithm.from_jwk(jwk)


def verify_token(token: str) -> dict[str, Any]:
    """Decode and validate a bearer token. Returns the claims dict on success."""

    audience = os.environ["AAD_AUDIENCE"]
    issuers  = _expected_issuers()

    public_key = _public_key_for(token)

    try:
        claims = jwt.decode(
            token,
            public_key,
            algorithms = ["RS256"],
            audience   = audience,
            issuer     = issuers,
            leeway     = 60,
            options    = {"require": ["exp", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError as e:
        raise TokenValidationError("Token expired") from e
    except jwt.InvalidAudienceError as e:
        raise TokenValidationError(f"Wrong audience; expected {audience}") from e
    except jwt.InvalidIssuerError as e:
        raise TokenValidationError(f"Wrong issuer; expected one of {issuers}") from e
    except jwt.InvalidTokenError as e:
        raise TokenValidationError(f"Token rejected: {e}") from e

    return claims
