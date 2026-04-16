"""
POST /deploys — trigger a deploy against UpdateSuiteAPI.

Flow:
  1. Validate project_key against the registry.
  2. Confirm the project has an `updatesuite_app` mapping.
  3. Call UpdateSuiteAPI's /deploy/{app}/{pipeline}.
  4. Write a DeployRecord audit row to dev_hub.Deployments.
  5. Return DevHub's DeployId alongside the upstream job_id.

DeployId is DevHub-owned and durable; upstream_job_id is the upstream
pointer used for polling status and logs.
"""
from fastapi import APIRouter, HTTPException, Request

from api._models        import DeployRequest, DeployResponse
from api.registry       import get_project
from api.repositories   import DeploymentsRepo


router = APIRouter(tags=["deploys"])


@router.post("/deploys", response_model=DeployResponse)
async def trigger_deploy(payload: DeployRequest, request: Request) -> DeployResponse:
    """Kick off a deploy by proxying to UpdateSuiteAPI and auditing it."""

    project = get_project(payload.project_key)

    if project is None:
        raise HTTPException(status_code=404, detail=f"Unknown project: {payload.project_key}")

    if not project.updatesuite_app:
        raise HTTPException(
            status_code = 400,
            detail      = f"Project {payload.project_key} has no updatesuite_app mapping",
        )

    client = request.app.state.updatesuite

    try:
        upstream = await client.trigger_deploy(
            app      = project.updatesuite_app,
            pipeline = payload.pipeline_key,
            params   = payload.params,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"UpdateSuite upstream error: {e}") from e

    upstream_job_id = upstream.get("job_id", "")
    status          = upstream.get("status", "queued")

    deploy_id = DeploymentsRepo.create(
        project_key     = payload.project_key,
        pipeline_key    = payload.pipeline_key,
        upstream_job_id = upstream_job_id,
        triggered_by    = None,              # will be AD user id once auth lands
        params          = payload.params,
    )

    return DeployResponse(
        deploy_id       = str(deploy_id),
        upstream_job_id = upstream_job_id,
        project_key     = payload.project_key,
        pipeline_key    = payload.pipeline_key,
        status          = status,
    )
