"""
Repository for dev_hub.UserRoles.

Authorization is resolved on every request: look up the email from the
validated JWT, return the role string, or None if the user is unknown
(which the dependency layer turns into a 403).

Emails are stored and looked up in lowercase — AAD's preferred_username
is usually mixed case depending on tenant config, so we normalize on
both write and read.
"""
import logging

from api._dataclasses.user_role import UserRole, Role
from api.db                     import get_connection


logger = logging.getLogger(__name__)


class UserRolesRepo:
    """All reads/writes against dev_hub.UserRoles."""

    @staticmethod
    def get_role(email: str) -> Role | None:
        """Return the role for an email, or None if not authorized."""

        sql = """
            SELECT Role
            FROM   dev_hub.UserRoles
            WHERE  Email = ?
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, email.lower())
            row = cur.fetchone()

        if row is None:
            return None

        return row[0]


    @staticmethod
    def get(email: str) -> UserRole | None:
        """Return the full UserRole row, or None."""

        sql = """
            SELECT Email, Role, CreatedAt, CreatedBy, Notes
            FROM   dev_hub.UserRoles
            WHERE  Email = ?
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, email.lower())
            row = cur.fetchone()

        if row is None:
            return None

        return UserRole(
            email      = row[0],
            role       = row[1],
            created_at = row[2],
            created_by = row[3],
            notes      = row[4],
        )


    @staticmethod
    def list_all() -> list[UserRole]:
        """Return every row, ordered by most-recently-created first."""

        sql = """
            SELECT Email, Role, CreatedAt, CreatedBy, Notes
            FROM   dev_hub.UserRoles
            ORDER BY CreatedAt DESC;
        """

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()

        return [
            UserRole(
                email      = r[0],
                role       = r[1],
                created_at = r[2],
                created_by = r[3],
                notes      = r[4],
            )
            for r in rows
        ]


    @staticmethod
    def upsert(email: str, role: Role, created_by: str | None = None, notes: str | None = None) -> None:
        """Insert or update a user's role. Admin utility — not exposed on the API yet."""

        sql = """
            MERGE dev_hub.UserRoles AS target
            USING (SELECT ? AS Email) AS src
                ON target.Email = src.Email

            WHEN MATCHED THEN UPDATE SET
                Role      = ?,
                Notes     = ?

            WHEN NOT MATCHED THEN INSERT (Email, Role, CreatedBy, Notes)
                VALUES (?, ?, ?, ?);
        """

        email_norm = email.lower()

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(
                sql,
                email_norm,
                # UPDATE
                role, notes,
                # INSERT
                email_norm, role, created_by, notes,
            )
            conn.commit()


    @staticmethod
    def delete(email: str) -> bool:
        """Remove a user's authorization. Returns True if a row was deleted."""

        sql = "DELETE FROM dev_hub.UserRoles WHERE Email = ?"

        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute(sql, email.lower())
            deleted = cur.rowcount > 0
            conn.commit()

        return deleted
