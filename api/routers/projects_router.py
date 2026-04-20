"""
GET /projects           — full project list from registry.json with cached health.
GET /projects/{key}     — single project lookup.

Health data is read from dev_hub.ProjectHealthLatest, populated by the
background health poller. Projects with no health_url have .health == None
permanently.
"""
from datetime import datetime

from fastapi  import APIRouter, Depends, HTTPException

from api._models        import ProjectHealth, ProjectInfo, ProjectsResponse
from api._dataclasses   import HealthSnapshot, ProjectEntry
from api.auth           import get_current_user
from api.registry       import get_project, get_registry
from api.repositories   import DeploymentsRepo, HealthRepo


router = APIRouter(tags=["projects"], dependencies=[Depends(get_current_user)])


def _to_health(snapshot: HealthSnapshot | None) -> ProjectHealth | None:
    """Coerce a HealthSnapshot dataclass into the API's ProjectHealth model."""

    if snapshot is None:
        return None

    return ProjectHealth(
        status      = snapshot.status,
        latency_ms  = snapshot.latency_ms,
        status_code = snapshot.status_code,
        checked_at  = snapshot.checked_at,
        error       = snapshot.error,
    )


def _serialize(
        entry:          ProjectEntry,
        health:         HealthSnapshot | None,
        last_deploy_at: datetime | None       = None) -> ProjectInfo:
    """Convert a ProjectEntry dataclass into its API-facing model."""

    return ProjectInfo(
        key                = entry.key,
        display_name       = entry.display_name,
        description        = entry.description,
        category           = entry.category,
        repo               = entry.repo,
        health_url         = entry.health_url,
        health_interval_s  = entry.health_interval_s,
        verify_tls         = entry.verify_tls,
        updatesuite_app    = entry.updatesuite_app,
        tags               = entry.tags,
        docs_paths         = entry.docs_paths,
        logs               = entry.logs,
        health             = _to_health(health),
        last_deploy_at     = last_deploy_at,
    )


@router.get("/projects", response_model=ProjectsResponse)
async def list_projects() -> ProjectsResponse:
    """Return every project in the registry with its latest health + deploy snapshot."""

    latest_health = HealthRepo.get_all_latest()
    latest_deploy = DeploymentsRepo.get_latest_success_per_project()

    projects = [
        _serialize(entry, latest_health.get(entry.key), latest_deploy.get(entry.key))
        for entry in get_registry().values()
    ]

    return ProjectsResponse(projects=projects)


@router.get("/projects/{key}", response_model=ProjectInfo)
async def get_project_by_key(key: str) -> ProjectInfo:
    """Return a single project by key with its latest health + deploy snapshot."""

    entry = get_project(key)

    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown project: {key}")

    return _serialize(
        entry,
        HealthRepo.get_latest(key),
        DeploymentsRepo.get_latest_success_per_project().get(key),
    )
