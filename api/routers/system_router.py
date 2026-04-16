"""
GET /system/status — reachability of DevHub's external dependencies.

Reports UpdateSuiteAPI, SQL Server, and (eventually) GitHub so the
frontend's system status strip can distinguish infra failures from
per-project health failures.
"""
import logging
import time

from datetime import datetime

from fastapi import APIRouter, Request

from api._models import SystemStatus, UpstreamCheck
from api.db      import ping as db_ping


logger = logging.getLogger(__name__)

router = APIRouter(tags=["system"])


async def _check_updatesuite(client) -> UpstreamCheck:
    """Probe UpdateSuiteAPI's /health endpoint."""

    started = time.perf_counter()

    try:
        await client.health()
        latency = int((time.perf_counter() - started) * 1000)

        return UpstreamCheck(
            name       = "updatesuite",
            status     = "up",
            latency_ms = latency,
            checked_at = datetime.now(),
        )

    except Exception as e:

        return UpstreamCheck(
            name       = "updatesuite",
            status     = "down",
            checked_at = datetime.now(),
            error      = str(e),
        )


def _check_db() -> UpstreamCheck:
    """Probe SQL Server reachability via a trivial SELECT 1."""

    started = time.perf_counter()
    ok      = db_ping()
    latency = int((time.perf_counter() - started) * 1000)

    return UpstreamCheck(
        name       = "database",
        status     = "up" if ok else "down",
        latency_ms = latency,
        checked_at = datetime.now(),
        error      = None if ok else "ping failed",
    )


def _check_github_stub() -> UpstreamCheck:
    """Stub check — real probe lands when GitHub integration ships."""

    return UpstreamCheck(
        name       = "github",
        status     = "unknown",
        checked_at = datetime.now(),
        error      = "not yet implemented",
    )


@router.get("/system/status", response_model=SystemStatus)
async def system_status(request: Request) -> SystemStatus:
    """Return reachability of every upstream DevHub depends on."""

    client = request.app.state.updatesuite

    return SystemStatus(
        updatesuite = await _check_updatesuite(client),
        database    = _check_db(),
        github      = _check_github_stub(),
    )
