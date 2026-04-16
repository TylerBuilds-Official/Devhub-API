"""
Point-in-time health probe result for a single project.

Persisted to DevHub.HealthHistory; most recent per project also kept
in-memory for fast dashboard reads.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class HealthSnapshot:
    """Single health probe result."""

    project_key:   str
    status:        str               # "up" | "down" | "degraded" | "unknown"
    latency_ms:    int | None
    status_code:   int | None
    checked_at:    datetime
    error:         str | None        = None
