"""
Persistent audit record for a deploy triggered through DevHub.

The live job state lives in UpdateSuiteAPI's JobManager (in-memory);
this record is the durable audit trail DevHub owns.
"""
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DeployRecord:
    """Audit record for a deploy triggered via DevHub."""

    deploy_id:         str
    project_key:       str
    pipeline_key:      str
    upstream_job_id:   str
    triggered_by:      str                # AD user once auth is wired; "anonymous" for now
    params:            dict               = field(default_factory=dict)
    status:            str                = "queued"
    started_at:        datetime | None    = None
    finished_at:       datetime | None    = None
    exit_code:         int | None         = None
    log_pointer:       str | None         = None
    error:             str | None         = None
