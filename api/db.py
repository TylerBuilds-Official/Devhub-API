"""
SQL Server connection holder for DevHub.

Targets TOOLBOX database, dev_hub schema. Uses pyodbc against the
existing SQL Server instance. Connection string comes from env; no
pooling layer beyond what pyodbc's driver provides — the project is
small enough that an ORM buys us nothing.

All persistence lives in api/repositories/ — this module owns only the
connection and a cheap ping for /system/status.
"""
import logging
import os

import pyodbc


logger = logging.getLogger(__name__)

DB_CONNECTION_STRING = os.getenv(
    "DEVHUB_DB_CONNECTION_STRING",
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=localhost;"
    "DATABASE=TOOLBOX;"
    "Trusted_Connection=yes;"
    "TrustServerCertificate=yes;"
)

SCHEMA = "dev_hub"


def get_connection() -> pyodbc.Connection:
    """Open a new pyodbc connection. Caller owns closing it."""

    return pyodbc.connect(DB_CONNECTION_STRING)


def ping() -> bool:
    """Quick reachability check for /system/status."""

    try:
        with get_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()

        return True

    except Exception as e:
        logger.warning(f"DB ping failed: {e}")

        return False
