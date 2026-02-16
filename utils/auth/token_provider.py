# auth/token_provider.py
# ─────────────────────────────────────────────────────────────────────────────
# Handles Azure AD token acquisition for SQL access.
#
# Two flows supported:
#   1. OBO (On-Behalf-Of)   – when deployed on Azure with Easy Auth enabled.
#                             The user's AAD access token is extracted from the
#                             X-MS-TOKEN-AAD-ACCESS-TOKEN request header and
#                             exchanged for a SQL-scoped token via MSAL OBO.
#   2. Client Credentials   – fallback for local development (no Easy Auth).
#                             Uses app registration credentials to acquire a
#                             token directly for the service principal.
#
# Public API:
#   get_token_provider(client_id, client_secret, tenant_id) -> Callable[[], dict]
#
#   The returned callable always yields:
#       { "access_token": str, "expires_on": float }   (unix timestamp)
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations

import base64
import json
import logging
from datetime import datetime
from typing import Callable

import msal
import streamlit as st

log = logging.getLogger(__name__)

SQL_SCOPE = ["https://database.windows.net//.default"]


# ─── MSAL client factory ─────────────────────────────────────────────────────

def _build_confidential_client(
    client_id: str,
    client_secret: str,
    tenant_id: str,
) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=client_id,
        client_credential=client_secret,
        authority=f"https://login.microsoftonline.com/{tenant_id}",
    )


# ─── Token flows ─────────────────────────────────────────────────────────────

def _token_to_result(msal_result: dict) -> dict:
    """Normalise an MSAL result into { access_token, expires_on }."""
    expires_on = datetime.now().timestamp() + float(msal_result.get("expires_in", 0))
    return {
        "access_token": msal_result["access_token"],
        "expires_on": expires_on,
    }


def _client_credentials_token(
    client_id: str,
    client_secret: str,
    tenant_id: str,
) -> dict:
    """Acquire a token as the service principal (local dev fallback)."""
    app = _build_confidential_client(client_id, client_secret, tenant_id)
    result = app.acquire_token_for_client(scopes=SQL_SCOPE)

    if "access_token" not in result: # type: ignore
        raise RuntimeError(
            f"Client-credentials token acquisition failed: "
            f"{result.get('error')} – {result.get('error_description')}" # type: ignore
        )

    _log_token_identity(result["access_token"], flow="client_credentials") # type: ignore
    return _token_to_result(result) # type: ignore


def _obo_token(
    user_access_token: str,
    client_id: str,
    client_secret: str,
    tenant_id: str,
) -> dict:
    """Exchange the user's AAD token for a SQL-scoped token via OBO."""
    app = _build_confidential_client(client_id, client_secret, tenant_id)
    result = app.acquire_token_on_behalf_of(
        user_assertion=user_access_token,
        scopes=SQL_SCOPE,
    )

    if "access_token" not in result:
        raise RuntimeError(
            f"OBO token acquisition failed: "
            f"{result.get('error')} – {result.get('error_description')}"
        )

    _log_token_identity(result["access_token"], flow="obo")
    return _token_to_result(result)


# ─── Debug helper ─────────────────────────────────────────────────────────────

def _log_token_identity(access_token: str, *, flow: str) -> None:
    """Decode and log the JWT identity claims (debug only – not security-sensitive)."""
    try:
        payload_b64 = access_token.split(".")[1]
        payload_b64 += "=" * (4 - len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload_b64))
        identity = claims.get("display_name") or claims.get("upn") or claims.get("appid", "unknown")
        log.debug("[%s] SQL token identity: %s (oid=%s)", flow, identity, claims.get("oid"))
    except Exception:
        log.debug("[%s] Could not decode token claims.", flow)


# ─── Header extraction ────────────────────────────────────────────────────────

def _get_easy_auth_token() -> str | None:
    """Return the user access token injected by Azure Easy Auth, or None."""
    try:
        ctx = getattr(st, "context", None)
        headers = ctx.headers if ctx else {}
        return (headers or {}).get("X-MS-TOKEN-AAD-ACCESS-TOKEN")
    except Exception:
        return None


# ─── Public factory ───────────────────────────────────────────────────────────

def get_token_provider(
    client_id: str,
    client_secret: str,
    tenant_id: str,
) -> Callable[[], dict]:
    """
    Return a zero-argument callable that yields a fresh SQL access token.

    The callable automatically selects OBO (when an Easy Auth header is
    present) or client-credentials (local dev) on every invocation.
    """

    def _provide() -> dict:
        user_token =  _get_easy_auth_token()
        if user_token:
            return _obo_token(user_token, client_id, client_secret, tenant_id)
        return _client_credentials_token(client_id, client_secret, tenant_id)

    return _provide
