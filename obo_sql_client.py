# obo_sql_client.py (rewritten)
# ---------------------------------------------------------------------
# OboSqlClient: Executes SQL using an access token supplier function.
# Token supplier returns { "access_token": str, "expires_on": float_timestamp }.
# Uses ONLY datetime for timestamp math. No 'time' module used.
# ---------------------------------------------------------------------

from datetime import datetime
import pandas as pd
import mssql_python

# ODBC driver attribute constant for AAD access token injection.
# SQL_COPT_SS_ACCESS_TOKEN = 1256
_SQL_COPT_SS_ACCESS_TOKEN = 1256


class OboSqlClient:
    def __init__(self, server: str, database: str, token_refresh_func):
        """
        :param server: e.g. 'sql-server-platform.database.windows.net'
        :param database: e.g. 'db-production-reports'
        :param token_refresh_func: callable -> dict {access_token, expires_on}
        """
        self.server = server
        self.database = database
        self.get_token = token_refresh_func
        self._cached_token: str | None = None
        self._token_expiry: float = 0.0  # unix timestamp (seconds)

    def _now_ts(self) -> float:
        return datetime.now().timestamp()

    def _ensure_valid_token(self) -> str:
        """Return a valid token, refreshing if < 5 minutes from expiry."""
        if (not self._cached_token) or (self._now_ts() > (self._token_expiry - 300)):
            token_response = self.get_token()
            self._cached_token = token_response["access_token"]
            self._token_expiry = float(token_response["expires_on"])
        return self._cached_token  # type: ignore

    @staticmethod
    def _encode_token(token: str) -> bytes:
        """
        Encode an AAD access token into the byte structure expected by the
        ODBC Driver 18 for SQL Server when passed via SQL_COPT_SS_ACCESS_TOKEN.

        The driver expects: 4-byte little-endian length prefix + UTF-16-LE token bytes.
        """
        token_bytes = token.encode("utf-16-le")
        return len(token_bytes).to_bytes(4, byteorder="little") + token_bytes

    def run_query(self, query: str) -> pd.DataFrame:
        """
        Execute a SQL query and return a pandas DataFrame.

        mssql_python does not accept a plain `access_token=` keyword argument.
        Instead, the AAD token must be injected via the ODBC `attrs_before` dict
        using the SQL_COPT_SS_ACCESS_TOKEN (1256) attribute key, with the token
        encoded as a length-prefixed UTF-16-LE byte struct.
        """
        token = self._ensure_valid_token()

        conn_str = (
            f"Server={self.server};"
            f"Database={self.database};"
            "Encrypt=YES;"
            "TrustServerCertificate=NO;"
        )

        token_struct = self._encode_token(token)

        with mssql_python.connect(
            conn_str,
            attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        ) as conn:
            cur = conn.cursor()
            cur.execute(query)
            rows = cur.fetchall()
            columns = [col[0] for col in cur.description] if cur.description else []

        return pd.DataFrame.from_records(rows, columns=columns)  # type: ignore