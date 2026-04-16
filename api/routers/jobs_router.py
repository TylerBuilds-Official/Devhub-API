"""
GET /jobs              — recent jobs from upstream.
GET /jobs/{deploy_id}  — single job status.
GET /jobs/{id}/log     — captured log buffer from upstream.

For MVP, deploy_id == upstream job_id, so proxying is straight-through.
When DB-backed audit lands, this layer will join DevHub's Deployments
table with the upstream live state.
"""
from fastapi import APIRouter, HTTPException, Request

from api._models import JobDetail, JobLogResponse, JobSummary, JobsResponse


router = APIRouter(tags=["jobs"])


def _to_summary(raw: dict, triggered_by: str = "anonymous") -> JobSummary:
    """Coerce an upstream JobSummary dict into DevHub's JobSummary shape."""

    return JobSummary(
        deploy_id          = raw.get("job_id", ""),
        upstream_job_id    = raw.get("job_id", ""),
        project_key        = raw.get("app", ""),
        pipeline_key       = raw.get("pipeline", ""),
        status             = raw.get("status", "unknown"),
        current_step       = raw.get("current_step", 0),
        total_steps        = raw.get("total_steps", 0),
        current_step_label = raw.get("current_step_label", ""),
        triggered_by       = triggered_by,
        started_at         = raw.get("started_at"),
        finished_at        = raw.get("finished_at"),
        error              = raw.get("error"),
    )


@router.get("/jobs", response_model=JobsResponse)
async def list_jobs(request: Request) -> JobsResponse:
    """Return recent jobs from UpdateSuiteAPI."""

    client = request.app.state.updatesuite

    try:
        upstream = await client.list_jobs()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UpdateSuite upstream error: {e}") from e

    jobs = [_to_summary(j) for j in upstream.get("jobs", [])]

    return JobsResponse(jobs=jobs)


@router.get("/jobs/{deploy_id}", response_model=JobDetail)
async def get_job(deploy_id: str, request: Request) -> JobDetail:
    """Return full state for a single job."""

    client = request.app.state.updatesuite

    try:
        raw = await client.get_job(deploy_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UpdateSuite upstream error: {e}") from e

    summary = _to_summary(raw)

    return JobDetail(**summary.model_dump(), params=raw.get("params", {}))


@router.get("/jobs/{deploy_id}/log", response_model=JobLogResponse)
async def get_job_log(deploy_id: str, request: Request) -> JobLogResponse:
    """Return the captured log buffer for a job."""

    client = request.app.state.updatesuite

    try:
        raw = await client.get_job_log(deploy_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UpdateSuite upstream error: {e}") from e

    return JobLogResponse(
        deploy_id = deploy_id,
        lines     = raw.get("lines", []),
    )
