"""
JWKS client for AAD token signature verification.

Microsoft rotates signing keys periodically, so we fetch the tenant's
public keys from the discovery endpoint and cache them for one hour.
On signature-mismatch (common right after key rotation) the verifier
can force a refresh via `invalidate()`.

This module is deliberately tiny — one cached dict of `{kid: jwk}` —
because the verifier is the only caller and we want a clear audit
surface for anything security-sensitive.
"""
import logging
import os
import time
from threading import Lock
from typing import Any

import httpx


logger = logging.getLogger(__name__)


_CACHE_TTL_S = 3600   # 1 hour; microsoft rotates keys on the order of days


class _JwksCache:
    """Thread-safe TTL cache of JWKS keyed by `kid`."""

    def __init__(self) -> None:
        self._keys:      dict[str, dict[str, Any]] = {}
        self._fetched_at: float = 0.0
        self._lock:       Lock = Lock()

    def _fresh(self) -> bool:
        return bool(self._keys) and (time.time() - self._fetched_at) < _CACHE_TTL_S

    def _fetch(self) -> None:
        url = os.environ["AAD_JWKS_URL"]

        logger.info(f"Fetching JWKS from {url}")

        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()

        payload = resp.json()
        self._keys       = {key["kid"]: key for key in payload.get("keys", [])}
        self._fetched_at = time.time()

        logger.info(f"Cached {len(self._keys)} JWKS keys")

    def get(self, kid: str) -> dict[str, Any] | None:
        with self._lock:
            if not self._fresh():
                self._fetch()
            return self._keys.get(kid)

    def invalidate(self) -> None:
        """Force the next get() to re-fetch — called on signature failures."""
        with self._lock:
            self._keys       = {}
            self._fetched_at = 0.0


_cache = _JwksCache()


def get_key(kid: str) -> dict[str, Any] | None:
    """Return the JWK dict for the given key id, refreshing cache if stale."""

    return _cache.get(kid)


def invalidate() -> None:
    """Drop the cache. Next call to get_key() re-fetches from Microsoft."""

    _cache.invalidate()
