"""
Upstream dependency exceptions — mostly UpdateSuiteAPI failures.

All inherit from UpstreamError so route handlers can catch the family
and surface a clean 502/503 to the frontend.
"""


class UpstreamError(Exception):
    """Base class for all upstream dependency errors."""


class UpdateSuiteUnreachableError(UpstreamError):
    """UpdateSuite API on the workstation is not reachable."""

    def __init__(self, base_url: str, reason: str):
        self.base_url = base_url
        self.reason   = reason
        super().__init__(f"UpdateSuite API at {base_url} unreachable: {reason}")


class UpstreamTimeoutError(UpstreamError):
    """An upstream call exceeded its timeout."""

    def __init__(self, base_url: str, timeout_s: float):
        self.base_url  = base_url
        self.timeout_s = timeout_s
        super().__init__(f"Upstream call to {base_url} timed out after {timeout_s}s")
