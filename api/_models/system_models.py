"""
Pydantic models for GET /system/status.

DevHub depends on three external things: UpdateSuiteAPI (workstation),
GitHub (docs/commits), and its own SQL Server. The status strip on the
frontend needs to tell these apart from per-project health.
"""
from datetime import datetime
from typing   import Literal

from pydantic import BaseModel


UpstreamStatus = Literal["up", "down", "unknown"]


class UpstreamCheck(BaseModel):
    name:       str
    status:     UpstreamStatus
    latency_ms: int | None    = None
    checked_at: datetime
    error:      str | None    = None


class SystemStatus(BaseModel):
    updatesuite: UpstreamCheck
    database:    UpstreamCheck
    github:      UpstreamCheck
