# db/pyodbc_client.py
# ─────────────────────────────────────────────────────────────────────────────
# PyodbcClient: SQL backend using `pyodbc` (drop-in swap for MssqlClient).
#
# Use this if mssql_python causes problems with OBO / token injection.
# pyodbc supports AAD access tokens via the SQL_COPT_SS_ACCESS_TOKEN connection
# attribute in exactly the same way as mssql_python, since both wrap ODBC 18.
#
# Switch backends in config.py – no other file needs to change.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import struct
from typing import Callable

import pandas as pd
import pyodbc

from .base import SqlClientBase

# ODBC attribute constant for AAD token injection.
_SQL_COPT_SS_ACCESS_TOKEN = 1256

# ODBC 18 driver string – must be installed in the container.
_DRIVER = "{ODBC Driver 18 for SQL Server}"


class PyodbcClient(SqlClientBase):
    """SQL client backed by :mod:`pyodbc`."""

    def __init__(self, server: str, database: str, token_provider: Callable[[], dict]):
        super().__init__(server, database, token_provider)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _encode_token(token: str) -> bytes:
        """
        Encode an AAD access token for pyodbc / ODBC 18.

        struct.pack packs a single unsigned int (I) in little-endian (<).
        Same wire format as the mssql_python backend.
        """
        token_bytes = token.encode("utf-16-le")
        return struct.pack("<I", len(token_bytes)) + token_bytes

    def _build_conn_str(self) -> str:
        return (
            f"DRIVER={_DRIVER};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            "Encrypt=yes;"
            "TrustServerCertificate=no;"
        )

    # ─── Public API ──────────────────────────────────────────────────────────

    def run_query(self, query: str) -> pd.DataFrame:
        token = self._ensure_valid_token()
        conn_str = self._build_conn_str()
        token_struct = self._encode_token(token)

        conn = pyodbc.connect(
            conn_str,
            attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        )
        try:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description] if cur.description else []
        finally:
            conn.close()

        return pd.DataFrame.from_records(rows, columns=columns) # type: ignore
