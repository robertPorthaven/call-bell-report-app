# db/mssql_client.py
# ─────────────────────────────────────────────────────────────────────────────
# MssqlClient: SQL backend using the `mssql_python` package.
#
# AAD tokens are injected via the ODBC SQL_COPT_SS_ACCESS_TOKEN (1256)
# attribute, encoded as a 4-byte little-endian length prefix followed by
# the token in UTF-16-LE.  This is the structure required by ODBC Driver 18.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from typing import Callable

import mssql_python
import pandas as pd

from .base import SqlClientBase

# ODBC attribute constant for AAD token injection (not exported by mssql_python).
_SQL_COPT_SS_ACCESS_TOKEN = 1256


class MssqlClient(SqlClientBase):
    """SQL client backed by :mod:`mssql_python`."""

    def __init__(self, server: str, database: str, token_provider: Callable[[], dict]):
        super().__init__(server, database, token_provider)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    @staticmethod
    def _encode_token(token: str) -> bytes:
        """
        Encode an AAD access token for the mssql_python / ODBC 18 driver.

        Format: 4-byte LE length of the UTF-16-LE token + UTF-16-LE token bytes.
        """
        token_bytes = token.encode("utf-16-le")
        return len(token_bytes).to_bytes(4, byteorder="little") + token_bytes

    def _build_conn_str(self) -> str:
        return (
            f"Server={self.server};"
            f"Database={self.database};"
            "Encrypt=YES;"
            "TrustServerCertificate=NO;"
        )

    # ─── Public API ──────────────────────────────────────────────────────────

    def run_query(self, query: str) -> pd.DataFrame:
        token = self._ensure_valid_token()
        conn_str = self._build_conn_str()
        token_struct = self._encode_token(token)

        with mssql_python.connect(
            conn_str,
            attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        ) as conn:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description] if cur.description else []

        return pd.DataFrame.from_records(rows, columns=columns) # type: ignore
