"""
FastAPI lifespan — startup/shutdown wiring.

On startup:
  1. Load registry.json into memory.
  2. Upsert every project into dev_hub.Projects so DB-side FKs resolve.
  3. Flag any row in the table not present in the registry as inactive.
  4. Instantiate the shared UpdateSuiteClient.
  5. Spawn the background health poller.

On shutdown:
  - Cancel the poller task and wait for it to unwind.
  - Close the httpx upstream client.

Long-lived singletons hang off app.state so route handlers grab them
via Request.app.state.
"""
import asyncio
import logging

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.health_poller    import run_poller
from api.registry         import get_registry, load_registry
from api.repositories     import ProjectsRepo
from api.upstream_client  import UpdateSuiteClient


logger = logging.getLogger(__name__)


def _sync_projects_to_db() -> None:
    """Mirror the in-memory registry into dev_hub.Projects."""

    registry = get_registry()

    for entry in registry.values():
        ProjectsRepo.upsert(entry)

    deactivated = ProjectsRepo.deactivate_missing(list(registry.keys()))

    logger.info(
        f"Synced {len(registry)} projects to dev_hub.Projects "
        f"({deactivated} deactivated)"
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize app-wide state on startup; clean up on shutdown."""

    load_registry()
    _sync_projects_to_db()

    app.state.updatesuite  = UpdateSuiteClient()
    app.state.poller_task  = asyncio.create_task(run_poller(), name="health_poller")

    logger.info("DevHub API startup complete")

    yield

    app.state.poller_task.cancel()

    try:
        await app.state.poller_task
    except asyncio.CancelledError:
        pass

    await app.state.updatesuite.close()

    logger.info("DevHub API shutdown complete")
