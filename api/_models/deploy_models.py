"""
Pydantic models for the POST /deploys endpoint.

DevHub's deploy endpoint is a thin proxy to UpdateSuiteAPI that also
creates a DeployRecord audit row and returns DevHub's deploy_id plus
the upstream job_id.
"""
from pydantic import BaseModel, Field

from api._models.job_models import JobStatus


class DeployRequest(BaseModel):
    """Deploy trigger request."""

    project_key:  str
    pipeline_key: str
    params:       dict = Field(default_factory=dict)


class DeployResponse(BaseModel):
    """Returned immediately after a deploy is queued upstream."""

    deploy_id:       str
    upstream_job_id: str
    project_key:     str
    pipeline_key:    str
    status:          JobStatus
