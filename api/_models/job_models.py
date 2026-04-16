"""
Pydantic models for the GET /jobs endpoints.

DevHub's job views merge upstream live state (polled from UpdateSuiteAPI)
with DevHub's own audit fields (triggered_by, deploy_id, created_at).
"""
from datetime import datetime
from pydantic import BaseModel


class JobSummary(BaseModel):
    """Lightweight job row for list views."""

    deploy_id:          str
    upstream_job_id:    str
    project_key:        str
    pipeline_key:       str
    status:             str
    current_step:       int
    total_steps:        int
    current_step_label: str
    triggered_by:       str
    started_at:         datetime | None
    finished_at:        datetime | None
    error:              str | None


class JobDetail(JobSummary):
    """Full job state including params."""

    params: dict


class JobsResponse(BaseModel):
    jobs: list[JobSummary]


class JobLogResponse(BaseModel):
    """Captured log buffer proxied from UpdateSuiteAPI."""

    deploy_id: str
    lines:     list[str]
