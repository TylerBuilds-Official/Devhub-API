"""
Repository for dev_hub.HealthHistory and dev_hub.ProjectHealthLatest.

Every probe appends a HealthHistory row and upserts ProjectHealthLatest
so the dashboard can read current status in O(projects) without a
TOP 1 subquery per card. History retention/cleanup is a scheduled job
for later; append-only for now.
"""
import logging

from api._dataclasses.health_snapshot import HealthSnapshot
from api.db                           import get_connection


logger = logging.getLogger(__name__)


class HealthRepo:
    """All reads/writes against dev_hub.HealthHistory + ProjectHealthLatest."""

    @staticmethod
    def record(snapshot: HealthSnapshot) -> None:
        """Append a history row and upsert the latest snapshot."""

        history_sql = """
            INSERT INTO dev_hub.HealthHistory (
                ProjectKey, Status, LatencyMs, StatusCode, CheckedAt, Error
            ) VALUES (?, ?, ?, ?, ?, ?);
        """

        latest_sql = """
            MERGE dev_hub.ProjectHealthLatest AS target
            USING (SELECT ? AS ProjectKey) AS src
            ON target.ProjectKey = src.ProjectKey

            WHEN MATCHED THEN UPDATE SET
                Status     = ?,
                LatencyMs  = ?,
                StatusCode = ?,
                CheckedAt  = ?,
                Error      = ?

            WHEN NOT MATCHED THEN INSERT (
                ProjectKey, Status, LatencyMs, StatusCode, CheckedAt, Error
            ) VALUES (?, ?, ?, ?, ?, ?);
        """

        with get_connection() as conn:
            cur = conn.cursor()

            cur.execute(
                history_sql,
                snapshot.project_key, snapshot.status, snapshot.latency_ms,
                snapshot.status_code, snapshot.checked_at, snapshot.error,
            )

            cur.execute(
                latest_sql,
                snapshot.project_key,
                # UPDATE
                snapshot.status, snapshot.latency_ms, snapshot.status_code,
                snapshot.checked_at, snapshot.error,
                # INSERT
                snapshot.project_key, snapshot.status, snapshot.latency_ms,
                snapshot.status_code, snapshot.checked_at, snapshot.error,
            )

            conn.commit()


    @staticmethod
    def get_latest(project_key: str) -> HealthSnapshot | None:
        """Return the most recent health snapshot for a project, or None."""

        sql = """
            SELECT ProjectKey, Status, LatencyMs, StatusCode, CheckedAt, Error
            FROM   dev_hub.ProjectHealthLatest
            WHERE  ProjectKey = ?;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, project_key)
            row = cur.fetchone()

        if row is None:
            return None

        return HealthSnapshot(
            project_key = row[0],
            status      = row[1],
            latency_ms  = row[2],
            status_code = row[3],
            checked_at  = row[4],
            error       = row[5],
        )


    @staticmethod
    def get_all_latest() -> dict[str, HealthSnapshot]:
        """Return a dict of latest snapshots keyed by project_key."""

        sql = """
            SELECT ProjectKey, Status, LatencyMs, StatusCode, CheckedAt, Error
            FROM   dev_hub.ProjectHealthLatest;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()

        return {
            r[0]: HealthSnapshot(
                project_key = r[0],
                status      = r[1],
                latency_ms  = r[2],
                status_code = r[3],
                checked_at  = r[4],
                error       = r[5],
            )
            for r in rows
        }
