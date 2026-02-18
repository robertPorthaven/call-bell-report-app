from helper.common_sql import SqlThings
import pandas as pd
import streamlit as st
from datetime import datetime
from helper.st_azure import get_azure_user
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required in production

# ─── Required environment variables ──────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
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
# ─────────────────────────────────────────────────────────────────────────────
# ENV VALIDATION & SETUP
# ─────────────────────────────────────────────────────────────────────────────
def validate_env() -> None:
    missing = [k for k, v in REQUIRED_VARS.items() if not v]
    if missing:
        st.error(f"### 🚨 Missing environment variables: {', '.join(missing)}")
        st.info(
            "For local dev, add these to a `.env` file next to app.py. "
            "In Azure Container Apps, set them under **Application settings**."
        )
        st.stop()
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

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────
etl_processor = SqlThings(
    SQL_SERVER, # type: ignore
    SQL_DATABASE, # type: ignore
    "call-bell-report-app",
)

@st.cache_data(show_spinner=True, ttl=1)
def load_home_metrics(start: datetime, end: datetime, home_name: str | None = None) -> tuple[pd.DataFrame, datetime]:
    df = etl_processor.read_tvf(
        st.session_state["user_context"],   # user_context
        "call_bell",                        # schema
        "fn_report_app_home_metrics",       # fn_name
        start,                              # @FirstDate (DATETIME2(0))
        end,                                # @LastDate  (DATETIME2(0))
        home_name                           # @home_name (VARCHAR(256) or None)
    )
    return df, datetime.now()

# @st.cache_data(show_spinner=True, ttl=5)
# def load_open_calls(hours: int = 24) -> tuple[pd.DataFrame, datetime]:
#     df = etl_processor.read_tvf(
#         st.session_state["user_context"],
#         "call_bell",
#         "fn_report_app_metrics",
#         2,
#         "Elizabeth Gardens",
#         1,
#         1,  
#     )
#     return df, datetime.now()