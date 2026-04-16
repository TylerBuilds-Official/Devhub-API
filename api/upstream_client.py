"""
httpx client for UpdateSuiteAPI on Tyler's workstation.

Thin wrapper — every endpoint on UpdateSuiteAPI gets a method here so
route handlers never deal with raw httpx. Shared secret auth goes in
once the upstream adds it; for MVP it's unauthenticated.
"""
import logging
import os

import httpx


logger = logging.getLogger(__name__)

UPDATESUITE_BASE_URL = os.getenv("UPDATESUITE_BASE_URL", "http://localhost:8765")
UPDATESUITE_TIMEOUT  = float(os.getenv("UPDATESUITE_TIMEOUT", "10.0"))


class UpdateSuiteClient:
    """Async httpx client for UpdateSuiteAPI."""

    def __init__(self, base_url: str = UPDATESUITE_BASE_URL, timeout: float = UPDATESUITE_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout  = timeout
        self._client  = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)


    async def health(self) -> dict:
        """GET /health on the upstream."""

        r = await self._client.get("/health")
        r.raise_for_status()

        return r.json()


    async def list_apps(self) -> dict:
        """GET /apps — the registry of upstream pipelines."""

        r = await self._client.get("/apps")
        r.raise_for_status()

        return r.json()


    async def trigger_deploy(self, app: str, pipeline: str, params: dict) -> dict:
        """POST /deploy/{app}/{pipeline} — kick off a job."""

        r = await self._client.post(
            f"/deploy/{app}/{pipeline}",
            json = {"params": params},
        )
        r.raise_for_status()

        return r.json()


    async def get_job(self, job_id: str) -> dict:
        """GET /jobs/{job_id} — current status."""

        r = await self._client.get(f"/jobs/{job_id}")
        r.raise_for_status()

        return r.json()


    async def get_job_log(self, job_id: str) -> dict:
        """GET /jobs/{job_id}/log — captured log buffer."""

        r = await self._client.get(f"/jobs/{job_id}/log")
        r.raise_for_status()

        return r.json()


    async def list_jobs(self) -> dict:
        """GET /jobs — recent upstream jobs."""

        r = await self._client.get("/jobs")
        r.raise_for_status()

        return r.json()


    async def close(self) -> None:
        """Dispose of the underlying httpx client."""

        await self._client.aclose()
