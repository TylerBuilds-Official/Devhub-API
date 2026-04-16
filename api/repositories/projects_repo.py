"""
Repository for dev_hub.Projects.

Projects are upserted from registry.json at startup — registry.json is
the authoritative source, the table is a cache so Deployments and
HealthHistory can FK into something. No separate CRUD API for projects;
edit registry.json and restart (or hit a future /admin/reload).
"""
import json
import logging

from api._dataclasses.project_entry import ProjectEntry
from api.db                         import get_connection


logger = logging.getLogger(__name__)


class ProjectsRepo:
    """All reads/writes against dev_hub.Projects."""

    @staticmethod
    def upsert(entry: ProjectEntry) -> None:
        """Insert or update a project row from a ProjectEntry."""

        tags_json  = json.dumps(entry.tags)       if entry.tags       else None
        docs_json  = json.dumps(entry.docs_paths) if entry.docs_paths else None

        sql = """
            MERGE dev_hub.Projects AS target
            USING (SELECT ? AS ProjectKey) AS src
            ON target.ProjectKey = src.ProjectKey

            WHEN MATCHED THEN UPDATE SET
                DisplayName      = ?,
                Description      = ?,
                Repo             = ?,
                Category         = ?,
                HealthUrl        = ?,
                UpdateSuiteApp   = ?,
                TagsJson         = ?,
                DocsPathsJson    = ?,
                IsActive         = 1,
                UpdatedAt        = GETDATE()

            WHEN NOT MATCHED THEN INSERT (
                ProjectKey, DisplayName, Description, Repo, Category,
                HealthUrl, UpdateSuiteApp, TagsJson, DocsPathsJson
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                sql,
                entry.key,
                # UPDATE
                entry.display_name, entry.description, entry.repo, entry.category,
                entry.health_url, entry.updatesuite_app, tags_json, docs_json,
                # INSERT
                entry.key, entry.display_name, entry.description, entry.repo, entry.category,
                entry.health_url, entry.updatesuite_app, tags_json, docs_json,
            )
            conn.commit()


    @staticmethod
    def deactivate_missing(active_keys: list[str]) -> int:
        """Flag any project not in active_keys as IsActive = 0."""

        if not active_keys:
            return 0

        placeholders = ",".join("?" * len(active_keys))
        sql          = f"""
            UPDATE dev_hub.Projects
            SET    IsActive  = 0,
                   UpdatedAt = GETDATE()
            WHERE  ProjectKey NOT IN ({placeholders})
              AND  IsActive   = 1;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, *active_keys)
            rows = cur.rowcount
            conn.commit()

        return rows
