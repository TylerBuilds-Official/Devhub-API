"""
GET /projects/{key}/logs — tail NSSM-managed log files for a project.

Reads directly from the local filesystem using paths declared in the
project's registry entry under `logs.{component}.{stream}`. DevHub must
be colocated with the log files — by design, since DevHub is deployed
to the same VM as the services it monitors.

Query params:
  - component  (required) — e.g. "api" or "frontend"
  - stream     (required) — "stdout" or "stderr"
  - tail       (optional, default 200, 1..5000)

Error shape:
  - 404 if project unknown
  - 404 if project has no logs block
  - 404 if requested component/stream not in the project's logs
  - 200 with `missing=True` + empty lines if path is valid but file is
    not yet on disk (common during initial deploy / before first log)
  - 502 if the file exists but can't be read (permissions, IO error)
"""
import logging

from fastapi import APIRouter, HTTPException, Query

from api._models       import LogsResponse
from api._models.log_models import LogStream
from api.log_reader    import LogFileMissingError, LogFileReadError, tail_file
from api.registry      import get_project


logger = logging.getLogger(__name__)

router = APIRouter(tags=["logs"])


@router.get("/projects/{key}/logs", response_model=LogsResponse)
async def get_project_logs(
        key:       str,
        component: str       = Query(..., description="Log component, e.g. 'api' or 'frontend'"),
        stream:    LogStream = Query(..., description="Which stream: 'stdout' or 'stderr'"),
        tail:      int       = Query(200, ge=1, le=5000) ) -> LogsResponse:
    """Return the last `tail` lines of a project's log file."""

    project = get_project(key)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Unknown project: {key}")

    if not project.logs:
        raise HTTPException(
            status_code = 404,
            detail      = f"Project {key} has no logs configured",
        )

    if component not in project.logs:
        raise HTTPException(
            status_code = 404,
            detail      = f"Project {key} has no '{component}' component; available: {list(project.logs.keys())}",
        )

    streams = project.logs[component]

    if stream not in streams:
        raise HTTPException(
            status_code = 404,
            detail      = f"Component '{component}' has no '{stream}' stream",
        )

    path = streams[stream]

    try:
        lines = tail_file(path, tail)

        return LogsResponse(
            project_key = key,
            component   = component,
            stream      = stream,
            path        = path,
            lines       = lines,
            missing     = False,
        )

    except LogFileMissingError:
        # Graceful: file not on disk yet (common in dev, or before first
        # service restart). Return empty lines + missing=True so the UI
        # can render a helpful message instead of treating it as an error.
        logger.info(f"Log file not present for {key}/{component}/{stream}: {path}")

        return LogsResponse(
            project_key = key,
            component   = component,
            stream      = stream,
            path        = path,
            lines       = [],
            missing     = True,
        )

    except LogFileReadError as e:
        logger.warning(f"Log read failed for {key}/{component}/{stream}: {e}")
        raise HTTPException(
            status_code = 502,
            detail      = f"Failed to read log file: {e}",
        ) from e
