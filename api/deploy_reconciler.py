"""
Deploy status reconciliation.

Update-on-read pattern: when a caller polls job status, we pull the
upstream state from UpdateSuiteAPI and patch dev_hub.Deployments if
the DB row is stale. This keeps the audit trail honest without a
background reconciler task.

Terminal statuses ("success", "failed") are never re-patched once set.

The passed-in DeployRecord is mutated in place so the caller's response
reflects the reconciled values without re-reading the row from DB.
"""
import logging

from api._dataclasses.deploy_record import DeployRecord
from api.repositories               import DeploymentsRepo


logger = logging.getLogger(__name__)

TERMINAL_STATUSES = {"success", "failed"}


def needs_reconcile(record: DeployRecord, upstream_status: str) -> bool:
    """Return True if the DB row should be patched from upstream state."""

    if record.status in TERMINAL_STATUSES:
        return False

    if record.status == upstream_status:
        return False

    return True


def reconcile(record: DeployRecord, upstream: dict) -> str:
    """Patch the Deployments row from upstream state; returns final status."""

    upstream_status = upstream.get("status", "unknown")

    if not needs_reconcile(record, upstream_status):
        return record.status

    new_started_at  = upstream.get("started_at")
    new_finished_at = upstream.get("finished_at")
    new_error       = upstream.get("error")

    DeploymentsRepo.update_status(
        deploy_id   = record.deploy_id,
        status      = upstream_status,
        started_at  = new_started_at,
        finished_at = new_finished_at,
        error       = new_error,
    )

    # Mirror the DB writes onto the in-memory record so the response
    # reflects reconciled values without re-reading. COALESCE semantics
    # on the SQL side mean None preserves existing DB values; do the
    # same here so we don't clobber real timestamps with None.
    record.status      = upstream_status
    if new_started_at  is not None: record.started_at  = new_started_at
    if new_finished_at is not None: record.finished_at = new_finished_at
    if new_error       is not None: record.error       = new_error

    logger.info(
        f"Reconciled deploy {record.deploy_id}: "
        f"{record.status} → {upstream_status}"
    )

    return upstream_status
