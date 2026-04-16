"""
Pydantic models for GET /projects/{key}/logs.
"""
from typing   import Literal

from pydantic import BaseModel


LogStream = Literal["stdout", "stderr"]


class LogsResponse(BaseModel):
    """Tail-N lines from one project component's log file."""

    project_key: str
    component:   str               # "api" | "frontend" (open-ended, registry-driven)
    stream:      LogStream
    path:        str               # echoed for debugging/observability
    lines:       list[str]
    missing:     bool = False      # True if file is not on disk
