"""
Project entry loaded from registry.json.

Source of truth for everything DevHub knows about a managed project:
identity, where it lives, how to probe it, and which UpdateSuite app
key maps to it (if deployable).

health_interval_s is an optional per-project override. When None, the
poller falls back to the global DEVHUB_HEALTH_INTERVAL_S.
"""
from dataclasses import dataclass, field


@dataclass
class ProjectEntry:
    """A single project managed by DevHub."""

    key:                str
    display_name:       str
    description:        str
    repo:               str               # github org/repo slug, e.g. "tyler/ScopeAnalysis"
    category:           str               # "service" | "engine" | "desktop" | "infra"
    health_url:         str | None        = None
    health_interval_s:  int | None        = None   # per-project override; None = use global
    updatesuite_app:    str | None        = None
    tags:               list[str]         = field(default_factory=list)
    docs_paths:         list[str]         = field(default_factory=list)
