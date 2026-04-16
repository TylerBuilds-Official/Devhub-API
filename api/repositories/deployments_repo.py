"""
Repository for dev_hub.Deployments.

Owns the audit trail for every deploy DevHub triggers. The live state
of a running job stays in UpdateSuiteAPI's in-memory JobManager; this
is the durable record DevHub owns.

DeployId is generated here (newid() server-side via OUTPUT) and returned
to the caller so the API response carries a DevHub-scoped id.
"""
import json
import logging

from datetime import datetime
from uuid     import UUID

from api._dataclasses.deploy_record import DeployRecord
from api.db                         import get_connection


logger = logging.getLogger(__name__)


class DeploymentsRepo:
    """All reads/writes against dev_hub.Deployments."""

    @staticmethod
    def create(
            project_key:     str,
            pipeline_key:    str,
            upstream_job_id: str,
            triggered_by:    int | None,
            params:          dict ) -> UUID:
        """Insert a new deployment row; returns the generated DeployId."""

        params_json = json.dumps(params) if params else None

        sql = """
            INSERT INTO dev_hub.Deployments (
                ProjectKey, PipelineKey, UpstreamJobId, TriggeredBy,
                ParamsJson, Status
            )
            OUTPUT inserted.DeployId
            VALUES (?, ?, ?, ?, ?, 'queued');
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                sql,
                project_key, pipeline_key, upstream_job_id, triggered_by,
                params_json,
            )
            row = cur.fetchone()
            conn.commit()

        return row[0]


    @staticmethod
    def update_status(
            deploy_id:   UUID | str,
            status:      str,
            started_at:  datetime | None  = None,
            finished_at: datetime | None  = None,
            exit_code:   int | None       = None,
            error:       str | None       = None ) -> None:
        """Patch the status + timing fields on an existing deployment."""

        sql = """
            UPDATE dev_hub.Deployments
            SET    Status       = ?,
                   StartedAt    = COALESCE(?, StartedAt),
                   FinishedAt   = COALESCE(?, FinishedAt),
                   ExitCode     = COALESCE(?, ExitCode),
                   ErrorMessage = COALESCE(?, ErrorMessage),
                   UpdatedAt    = GETDATE()
            WHERE  DeployId     = ?;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, status, started_at, finished_at, exit_code, error, str(deploy_id))
            conn.commit()


    @staticmethod
    def get_by_id(deploy_id: UUID | str) -> DeployRecord | None:
        """Look up a single deployment row by DeployId."""

        sql = """
            SELECT DeployId, ProjectKey, PipelineKey, UpstreamJobId, TriggeredBy,
                   ParamsJson, Status, StartedAt, FinishedAt, ExitCode,
                   LogPointer, ErrorMessage
            FROM   dev_hub.Deployments
            WHERE  DeployId = ?;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, str(deploy_id))
            row = cur.fetchone()

        if row is None:
            return None

        return _row_to_record(row)


    @staticmethod
    def get_by_upstream_job_id(upstream_job_id: str) -> DeployRecord | None:
        """Look up a single deployment row by its upstream job_id."""

        sql = """
            SELECT DeployId, ProjectKey, PipelineKey, UpstreamJobId, TriggeredBy,
                   ParamsJson, Status, StartedAt, FinishedAt, ExitCode,
                   LogPointer, ErrorMessage
            FROM   dev_hub.Deployments
            WHERE  UpstreamJobId = ?;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, upstream_job_id)
            row = cur.fetchone()

        if row is None:
            return None

        return _row_to_record(row)


    @staticmethod
    def list_recent(limit: int = 50, project_key: str | None = None) -> list[DeployRecord]:
        """Return the most recent deployments, optionally filtered by project."""

        if project_key is None:
            sql = """
                SELECT TOP (?)
                       DeployId, ProjectKey, PipelineKey, UpstreamJobId, TriggeredBy,
                       ParamsJson, Status, StartedAt, FinishedAt, ExitCode,
                       LogPointer, ErrorMessage
                FROM   dev_hub.Deployments
                ORDER BY CreatedAt DESC;
            """
            args = (limit,)

        else:
            sql = """
                SELECT TOP (?)
                       DeployId, ProjectKey, PipelineKey, UpstreamJobId, TriggeredBy,
                       ParamsJson, Status, StartedAt, FinishedAt, ExitCode,
                       LogPointer, ErrorMessage
                FROM   dev_hub.Deployments
                WHERE  ProjectKey = ?
                ORDER BY CreatedAt DESC;
            """
            args = (limit, project_key)

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, *args)
            rows = cur.fetchall()

        return [_row_to_record(r) for r in rows]


def _row_to_record(row) -> DeployRecord:
    """Map a pyodbc Deployments row to a DeployRecord dataclass."""

    return DeployRecord(
        deploy_id       = str(row[0]),
        project_key     = row[1],
        pipeline_key    = row[2],
        upstream_job_id = row[3],
        triggered_by    = str(row[4]) if row[4] is not None else "anonymous",
        params          = json.loads(row[5]) if row[5] else {},
        status          = row[6],
        started_at      = row[7],
        finished_at     = row[8],
        exit_code       = row[9],
        log_pointer     = row[10],
        error           = row[11],
    )
