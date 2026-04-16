"""
Background health poller.

Probes every project's health_url on a per-project cadence, writes the
result to dev_hub.HealthHistory, and upserts dev_hub.ProjectHealthLatest
so the dashboard can read current status in O(projects).

Architecture:
  - One supervisor asyncio.Task owned by lifespan.
  - For each project with a health_url, one child task loops on that
    project's cadence with its own httpx.AsyncClient (so verify_tls
    can vary per project).
  - Cadence resolves per project: project.health_interval_s if set,
    else DEVHUB_HEALTH_INTERVAL_S from env, else DEFAULT_INTERVAL_S.

Probe classification:
  - 2xx              → "up"
  - 3xx/4xx/5xx      → "degraded"  (reachable, bad response)
  - connection error → "down"
  - timeout          → "down"
  - no health_url    → skipped entirely
"""
import asyncio
import logging
import os
import time

from datetime import datetime

from httpx import AsyncClient, HTTPError, TimeoutException

from api._dataclasses.health_snapshot import HealthSnapshot
from api._dataclasses.project_entry   import ProjectEntry
from api.registry                     import get_registry
from api.repositories                 import HealthRepo


logger = logging.getLogger(__name__)

DEFAULT_INTERVAL_S  = 60
PROBE_TIMEOUT_S     = 5.0


def _global_interval() -> int:
    """Global default probe interval in seconds. Env-overridable."""

    raw = os.getenv("DEVHUB_HEALTH_INTERVAL_S")

    if raw is None:
        return DEFAULT_INTERVAL_S

    try:
        return int(raw)
    except ValueError:
        logger.warning(f"Invalid DEVHUB_HEALTH_INTERVAL_S={raw!r}, using {DEFAULT_INTERVAL_S}s")

        return DEFAULT_INTERVAL_S


def _resolve_interval(project: ProjectEntry) -> int:
    """Project override wins; falls back to global."""

    if project.health_interval_s is not None:
        return project.health_interval_s

    return _global_interval()


async def _probe_once(client: AsyncClient, project: ProjectEntry) -> HealthSnapshot:
    """Execute one health probe against a project's health_url."""

    url     = project.health_url
    started = time.perf_counter()

    try:
        r          = await client.get(url, timeout=PROBE_TIMEOUT_S)
        latency_ms = int((time.perf_counter() - started) * 1000)

        if 200 <= r.status_code < 300:
            status = "up"
            error  = None
        else:
            status = "degraded"
            error  = f"HTTP {r.status_code}"

        return HealthSnapshot(
            project_key = project.key,
            status      = status,
            latency_ms  = latency_ms,
            status_code = r.status_code,
            checked_at  = datetime.now(),
            error       = error,
        )

    except TimeoutException:

        return HealthSnapshot(
            project_key = project.key,
            status      = "down",
            latency_ms  = None,
            status_code = None,
            checked_at  = datetime.now(),
            error       = f"timeout after {PROBE_TIMEOUT_S}s",
        )

    except HTTPError as e:

        return HealthSnapshot(
            project_key = project.key,
            status      = "down",
            latency_ms  = None,
            status_code = None,
            checked_at  = datetime.now(),
            error       = str(e),
        )

    except Exception as e:
        logger.exception(f"Unexpected probe error for {project.key}")

        return HealthSnapshot(
            project_key = project.key,
            status      = "down",
            latency_ms  = None,
            status_code = None,
            checked_at  = datetime.now(),
            error       = f"unexpected: {e}",
        )


async def _project_loop(project: ProjectEntry) -> None:
    """Probe a single project forever on its resolved cadence."""

    interval = _resolve_interval(project)

    logger.info(
        f"Health poller: {project.key} every {interval}s → "
        f"{project.health_url} (verify_tls={project.verify_tls})"
    )

    async with AsyncClient(verify=project.verify_tls) as client:
        while True:
            try:
                snapshot = await _probe_once(client, project)
                HealthRepo.record(snapshot)

            except asyncio.CancelledError:
                raise

            except Exception:
                logger.exception(f"Health poller tick failed for {project.key}")

            await asyncio.sleep(interval)


async def run_poller() -> None:
    """Supervisor coroutine — fans out one loop per probeable project."""

    registry   = get_registry()
    probeable  = [p for p in registry.values() if p.health_url]

    if not probeable:
        logger.info("Health poller: no projects with health_url — nothing to poll")

        return

    logger.info(
        f"Health poller: starting {len(probeable)} project loop(s) "
        f"(global default {_global_interval()}s)"
    )

    tasks = [
        asyncio.create_task(_project_loop(p), name=f"health:{p.key}")
        for p in probeable
    ]

    try:
        await asyncio.gather(*tasks)

    except asyncio.CancelledError:
        logger.info("Health poller: shutdown signal received")

        for t in tasks:
            t.cancel()

        await asyncio.gather(*tasks, return_exceptions=True)

        raise
