"""Custom exceptions for DevHub API — one concept per file."""

from api._errors.project_errors  import (
    ProjectError,
    UnknownProjectError,
    RegistryLoadError,
)
from api._errors.upstream_errors import (
    UpstreamError,
    UpdateSuiteUnreachableError,
    UpstreamTimeoutError,
)


__all__ = [
    "ProjectError",
    "UnknownProjectError",
    "RegistryLoadError",
    "UpstreamError",
    "UpdateSuiteUnreachableError",
    "UpstreamTimeoutError",
]
