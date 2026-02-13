# config.py
# ─────────────────────────────────────────────────────────────────────────────
# Central configuration.
#
# • Reads all required environment variables.
# • Exposes the SQL_BACKEND alias – change ONE line here to swap the driver.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required in production

# ─── Required environment variables ──────────────────────────────────────────

AZURE_CLIENT_ID: str     = os.environ.get("AZURE_CLIENT_ID", "")
AZURE_CLIENT_SECRET: str = os.environ.get("AZURE_CLIENT_SECRET", "")
AZURE_TENANT_ID: str     = os.environ.get("AZURE_TENANT_ID", "")
SQL_SERVER: str          = os.environ.get("SQL_SERVER", "")
SQL_DATABASE: str        = os.environ.get("SQL_DATABASE", "")

REQUIRED_VARS: dict[str, str] = {
    "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
    "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
    "AZURE_TENANT_ID": AZURE_TENANT_ID,
    "SQL_SERVER": SQL_SERVER,
    "SQL_DATABASE": SQL_DATABASE,
}

# ─── SQL backend selector ─────────────────────────────────────────────────────
#
# Change this import to switch the driver for the entire app.
# Options:
#   from db.mssql_client import MssqlClient as SQL_BACKEND
#   from db.pyodbc_client import PyodbcClient as SQL_BACKEND

from db.pyodbc_client import PyodbcClient as SQL_BACKEND  # noqa: E402  (intentional late import)
