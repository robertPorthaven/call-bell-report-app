# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Call Bell Dashboard – Streamlit entry point.
#
# This file is intentionally thin: it wires config → auth → db together and
# owns only the Streamlit UI.  All SQL / token logic lives in auth/ and db/.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
from datetime import datetime
import json
import base64
import pandas as pd
import streamlit as st
from helper.aagrid_dataframe import render_call_grid
from helper.components import render_event_pills
from helper.common_sql import SqlThings
from helper.st_azure import get_azure_user
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
AMBER = "#f09c2e"
OCEAN = "#3e6f86"
SLATE = "#757a6e"

REQUIRED_VARS: dict[str, str] = {
    "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
    "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
    "AZURE_TENANT_ID": AZURE_TENANT_ID,
    "SQL_SERVER": SQL_SERVER,
    "SQL_DATABASE": SQL_DATABASE,
}

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Call Bell Dashboard",
    page_icon="assets/image.png",
    layout="wide",
)
with open("assets/style.css", "r", encoding="utf-8") as css_file:
    st.write(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
# ENV VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def _validate_env() -> None:
    missing = [k for k, v in REQUIRED_VARS.items() if not v]
    if missing:
        st.error(f"### 🚨 Missing environment variables: {', '.join(missing)}")
        st.info(
            "For local dev, add these to a `.env` file next to app.py. "
            "In Azure Container Apps, set them under **Application settings**."
        )
        st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL ERROR PAGE
# ─────────────────────────────────────────────────────────────────────────────

def _fatal_page(exc: Exception) -> None:
    timestamp = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    st.markdown(
        f"""
        ### 🚨 System Error
        The application encountered a critical issue and cannot continue.  
        **Time of failure:** {timestamp}  
        Please notify the data bunny 🐰.
        > "Errors happen. Great dashboards handle them gracefully."
        """,
        unsafe_allow_html=True,
    )
    st.exception(exc)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
# Initialize on first load
if "user_context" not in st.session_state:
    # Check if running locally (no Azure headers available)
    is_local = os.environ.get("LOCAL_DEV", "false").lower() == "true"
    
    if is_local:
        # Local development: use mock user
        st.session_state["user_context"] = {
            "app_user": os.environ.get("DEV_USER_EMAIL", "dev@example.com"),
            "app_user_oid": "local-dev-guid-12345",
            "source_app": "call-bell-report-app"
        }
    else:
        # Production: get real Azure user
        user = get_azure_user() or {}
        
        # Build context, filtering out None values (SQL can't handle them)
        context = {
            "source_app": "call-bell-report-app"
        }
        
        if user.get("email"):
            context["app_user"] = user["email"] # type: ignore
        if user.get("oid"):
            context["app_user_oid"] = user["oid"] # type: ignore
        
        st.session_state["user_context"] = context

etl_processor = SqlThings(
    SQL_SERVER, # type: ignore
    SQL_DATABASE, # type: ignore
    "call-bell-report-app",
)

@st.cache_data(show_spinner=True, ttl=5)
def load_open_calls(hours: int = 24) -> tuple[pd.DataFrame, datetime]:
    df = etl_processor.read_tvf(
        "call_bell",
        "fn_report_app_open_events",
        2,
        "Avondale"
        ,user_context=st.session_state["user_context"]
    )
    return df, datetime.now()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

try:
    _validate_env()

    st.title("Call Bell Report")

    df, updated_at = load_open_calls(24)
    st.caption(f"Refreshed: {updated_at:%d/%m/%y %H:%M:%S}")
    st.subheader("Active Open Calls")
    # Convert event data to colour coded svgs and then draw the Open Call table
    df_open_calls = df[["Room Location","Call Type","Start","Total Time","Waiting Time","Care Time","Events"]]
    df_open_calls["Events"] = render_event_pills(df["Events"]) 
    render_call_grid(df_open_calls, "open_calls_grid", theme_color=AMBER, )



# ─────────────────────────────────────────────────────────────────────────────
# DEBUGGING / AUTH DIAGNOSTICS
# ─────────────────────────────────────────────────────────────────────────────

    is_local = os.environ.get("LOCAL_DEV", "false").lower() == "true"
    if is_local:
        st.info("🏠 **LOCAL DEVELOPMENT MODE** - Using mock user. Set DEV_USER_EMAIL to customize.")

    with st.expander("🔎 Auth diagnostics (temporary)"):
        st.write(f"**Mode:** {'Local Development' if is_local else 'Production (Azure)'}")
        
        st.write("**Extracted User:**")
        if not is_local:
            user = get_azure_user()
            st.json(user if user else {"status": "No user found"})
        else:
            st.write("N/A (using local dev mode)")
        
        st.write("**Session Context (sent to SQL):**")
        st.json(st.session_state.get("user_context", {}))
        
        st.write("**Environment variables:**")
        env_hits = {k: "•••present•••" for k in os.environ.keys() if "MS" in k or "CLIENT" in k or "PRINCIPAL" in k}
        st.write(env_hits or "No auth-related env vars found")
        
        st.write("**Request headers:**")
        try:
            headers = st.context.headers
            auth_headers = {k: v[:50] + "..." if len(v) > 50 else v 
                          for k, v in headers.items() 
                          if "principal" in k.lower() or "client" in k.lower() or "ms" in k.lower()}
            st.write(auth_headers or "No auth-related headers found")
            
            # Try to decode principal if present
            principal_header = headers.get("X-Ms-Client-Principal") or headers.get("x-ms-client-principal")
            if principal_header:
                try:
                    decoded = base64.b64decode(principal_header).decode("utf-8")
                    st.write("**Decoded principal:**")
                    st.json(json.loads(decoded))
                except Exception as e:
                    st.write(f"Principal decode error: {e}")
        except (AttributeError, RuntimeError) as e:
            st.write(f"Cannot access headers (Streamlit < 1.18.0 or outside request context): {e}")

except Exception as exc:
    _fatal_page(exc)