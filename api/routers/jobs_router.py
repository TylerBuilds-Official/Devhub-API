"""
GET /jobs              — recent deploys from dev_hub.Deployments.
GET /jobs/{deploy_id}  — single job status, reconciled against upstream.
GET /jobs/{id}/log     — captured log buffer from upstream.

Update-on-read: every detail fetch pulls upstream state and patches the
Deployments row if it's stale. Terminal statuses are never re-patched.

The list endpoint reads directly from dev_hub.Deployments (no upstream
call per item — that would be expensive and redundant). Stale rows in
the list get corrected the moment anyone opens their detail view.
"""
import logging

from fastapi import APIRouter, HTTPException, Query, Request

from api._dataclasses.deploy_record import DeployRecord
from api._models                    import JobDetail, JobLogResponse, JobSummary, JobsResponse
from api.deploy_reconciler          import reconcile
from api.repositories               import DeploymentsRepo


logger = logging.getLogger(__name__)

router = APIRouter(tags=["jobs"])


def _record_to_summary(record: DeployRecord, upstream: dict | None = None) -> JobSummary:
    """Build a JobSummary by merging the DB row with optional upstream state."""

    upstream           = upstream or {}
    current_step       = upstream.get("current_step", 0)
    total_steps        = upstream.get("total_steps", 0)
    current_step_label = upstream.get("current_step_label", "")

    return JobSummary(
        deploy_id          = record.deploy_id,
        upstream_job_id    = record.upstream_job_id,
        project_key        = record.project_key,
        pipeline_key       = record.pipeline_key,
        status             = record.status,
        current_step       = current_step,
        total_steps        = total_steps,
        current_step_label = current_step_label,
        triggered_by       = record.triggered_by,
        started_at         = record.started_at,
        finished_at        = record.finished_at,
        error              = record.error,
    )


@router.get("/jobs", response_model=JobsResponse)
async def list_jobs(
        limit:       int         = Query(50, ge=1, le=500),
        project_key: str | None  = Query(None, description="Filter to a single project") ) -> JobsResponse:
    """Return recent deploys from the DevHub audit table."""

    records = DeploymentsRepo.list_recent(limit=limit, project_key=project_key)
    jobs    = [_record_to_summary(r) for r in records]

    return JobsResponse(jobs=jobs)


@router.get("/jobs/{deploy_id}", response_model=JobDetail)
async def get_job(deploy_id: str, request: Request) -> JobDetail:
    """Return full state for a single job, reconciled against upstream."""

    record = DeploymentsRepo.get_by_id(deploy_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown deploy: {deploy_id}")

    client   = request.app.state.updatesuite
    upstream: dict = {}

    try:
        upstream = await client.get_job(record.upstream_job_id)
        reconcile(record, upstream)    # mutates record in place

    except Exception as e:
        # Upstream may legitimately not have the job (e.g., job cache
        # eviction on workstation restart). Fall through with the DB row
        # as-is rather than failing the read.
        logger.warning(
            f"Upstream lookup failed for deploy {deploy_id} "
            f"(upstream_job_id={record.upstream_job_id}): {e}"
        )

    summary = _record_to_summary(record, upstream)

    return JobDetail(**summary.model_dump(), params=record.params)


@router.get("/jobs/{deploy_id}/log", response_model=JobLogResponse)
async def get_job_log(deploy_id: str, request: Request) -> JobLogResponse:
    """Return the captured log buffer for a job."""

    record = DeploymentsRepo.get_by_id(deploy_id)

    if record is None:
        raise HTTPException(status_code=404, detail=f"Unknown deploy: {deploy_id}")

    client = request.app.state.updatesuite

    try:
        raw = await client.get_job_log(record.upstream_job_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UpdateSuite upstream error: {e}") from e

    return JobLogResponse(
        deploy_id = deploy_id,
        lines     = raw.get("lines", []),
    )
