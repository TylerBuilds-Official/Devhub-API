"""
Project entry loaded from registry.json.

Source of truth for everything DevHub knows about a managed project:
identity, where it lives, how to probe it, and which UpdateSuite app
key maps to it (if deployable).

health_interval_s is an optional per-project override. When None, the
poller falls back to the global DEVHUB_HEALTH_INTERVAL_S.

verify_tls toggles httpx cert verification on the health probe. Defaults
to True; set False for services behind self-signed certs (FabCore).

repo is None when no GitHub repo is configured — the frontend renders
"no repo linked" rather than a broken link.

logs is an optional nested dict keyed by component name (e.g. "api",
"frontend") whose values are {stdout, stderr} pairs of absolute paths
to NSSM-managed log files. Absent → project has no viewable logs.
"""
from dataclasses import dataclass, field


@dataclass
class ProjectEntry:
    """A single project managed by DevHub."""

    key:                str
    display_name:       str
    description:        str
    category:           str                      # "service" | "frontend" | "desktop" | "infra"
    repo:               str | None                        = None
    health_url:         str | None                        = None
    health_interval_s:  int | None                        = None   # per-project override; None = use global
    verify_tls:         bool                              = True   # False for self-signed https endpoints
    updatesuite_app:    str | None                        = None
    tags:               list[str]                         = field(default_factory=list)
    docs_paths:         list[str]                         = field(default_factory=list)
    logs:               dict[str, dict[str, str]] | None  = None   # {component: {stdout|stderr: path}}
