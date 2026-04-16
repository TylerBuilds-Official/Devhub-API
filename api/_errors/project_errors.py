"""
Project/registry related exceptions raised by the API layer.

All inherit from ProjectError so route handlers can catch the family.
"""


class ProjectError(Exception):
    """Base class for all project/registry errors."""


class UnknownProjectError(ProjectError):
    """The requested project key is not in the registry."""

    def __init__(self, key: str):
        self.key = key
        super().__init__(f"Unknown project: {key}")


class RegistryLoadError(ProjectError):
    """registry.json failed to load or parse."""

    def __init__(self, path: str, reason: str):
        self.path   = path
        self.reason = reason
        super().__init__(f"Failed to load registry at {path}: {reason}")
