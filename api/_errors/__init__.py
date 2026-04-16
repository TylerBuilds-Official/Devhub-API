"""Custom exceptions for DevHub API — one concept per file."""

from api._errors.project_errors  import (
    ProjectError,
    RegistryLoadError,
)


__all__ = [
    "ProjectError",
    "RegistryLoadError",
]
