"""
Pydantic models for the GET /projects endpoints.
"""
from datetime import datetime
from pydantic import BaseModel


class ProjectHealth(BaseModel):
    status:      str
    latency_ms:  int | None      = None
    status_code: int | None      = None
    checked_at:  datetime | None = None
    error:       str | None      = None


class ProjectInfo(BaseModel):
    key:             str
    display_name:    str
    description:     str
    category:        str
    repo:            str | None           = None
    health_url:      str | None           = None
    verify_tls:      bool                 = True
    updatesuite_app: str | None           = None
    tags:            list[str]            = []
    docs_paths:      list[str]            = []
    health:          ProjectHealth | None = None


class ProjectsResponse(BaseModel):
    projects: list[ProjectInfo]
