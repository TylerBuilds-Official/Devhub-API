"""
Registry loader for DevHub's managed projects.

Loads resources/registry.json at startup into an in-memory dict of
ProjectEntry instances keyed by project key. Hot-reloadable via a
reload() call; no file watcher for MVP.
"""
import json
import logging

from pathlib import Path

from api._dataclasses.project_entry import ProjectEntry
from api._errors.project_errors     import RegistryLoadError


logger = logging.getLogger(__name__)

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "resources" / "registry.json"

_REGISTRY: dict[str, ProjectEntry] = {}


def load_registry(path: Path = REGISTRY_PATH) -> dict[str, ProjectEntry]:
    """Load registry.json from disk into the module-level _REGISTRY dict."""

    global _REGISTRY

    if not path.exists():
        raise RegistryLoadError(str(path), "file not found")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise RegistryLoadError(str(path), f"invalid JSON: {e}") from e

    projects = raw.get("projects", [])
    loaded   = {}

    for entry in projects:
        try:
            pe = ProjectEntry(
                key               = entry["key"],
                display_name      = entry["display_name"],
                description       = entry.get("description", ""),
                category          = entry.get("category", "service"),
                repo              = entry.get("repo"),
                health_url        = entry.get("health_url"),
                health_interval_s = entry.get("health_interval_s"),
                verify_tls        = entry.get("verify_tls", True),
                updatesuite_app   = entry.get("updatesuite_app"),
                tags              = entry.get("tags", []),
                docs_paths        = entry.get("docs_paths", []),
                logs              = entry.get("logs"),
            )
        except KeyError as e:
            raise RegistryLoadError(str(path), f"entry missing required field: {e}") from e

        loaded[pe.key] = pe

    _REGISTRY = loaded

    logger.info(f"Loaded {len(_REGISTRY)} projects from registry")

    return _REGISTRY


def get_registry() -> dict[str, ProjectEntry]:
    """Return the current in-memory registry. Call load_registry() at startup first."""

    return _REGISTRY


def get_project(key: str) -> ProjectEntry | None:
    """Look up a single project by key; returns None if not found."""

    return _REGISTRY.get(key)
