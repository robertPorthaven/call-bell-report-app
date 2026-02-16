# db/base.py
# ─────────────────────────────────────────────────────────────────────────────
# SqlClientBase: Abstract contract for token-authenticated SQL clients.
#
# Both concrete backends (mssql_python and pyodbc) implement this interface,
# so the rest of the app only ever depends on SqlClientBase.  To swap the
# backend you change one line in config.py.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable

import pandas as pd


class SqlClientBase(ABC):
    """
    Base class for token-authenticated SQL query runners.

    Subclasses must implement :meth:`_open_connection` and
    :meth:`run_query`.  Token caching (5-minute refresh buffer) is
    handled here so each backend doesn't have to repeat it.
    """

    # Refresh the token when fewer than this many seconds remain.
    _REFRESH_BUFFER_SECS: int = 300

    def __init__(self, server: str, database: str, token_provider: Callable[[], dict]):
        """
        :param server:         FQDN of the Azure SQL server.
        :param database:       Target database name.
        :param token_provider: Zero-arg callable -> {access_token, expires_on}.
        """
        self.server = server
        self.database = database
        self._get_token = token_provider
        self._cached_token: str | None = None
        self._token_expiry: float = 0.0  # unix timestamp

    # ─── Token management (shared) ───────────────────────────────────────────

    def _now_ts(self) -> float:
        return datetime.now().timestamp()

    def _ensure_valid_token(self) -> str:
        """Return a cached token, refreshing proactively near expiry."""
        deadline = self._token_expiry - self._REFRESH_BUFFER_SECS
        if (not self._cached_token) or (self._now_ts() > deadline):
            resp = self._get_token()
            self._cached_token = resp["access_token"]
            self._token_expiry = float(resp["expires_on"])
        return self._cached_token  # type: ignore[return-value]

    # ─── Abstract interface ───────────────────────────────────────────────────

    @abstractmethod
    def run_query(self, query: str) -> pd.DataFrame:
        """Execute *query* and return all rows as a DataFrame."""
        ...
