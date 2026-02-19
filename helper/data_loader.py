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

cache_timer_today = 50
@st.cache_data(show_spinner=True, ttl=cache_timer_today)
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

@st.cache_data(show_spinner=True, ttl=cache_timer_today)
def load_homes() -> pd.DataFrame:
    df = etl_processor.run_query_df(
        st.session_state["user_context"],   
        "SELECT*FROM[call_bell].[vw_report_app_list_homes]",     
    )
    return df

@st.cache_data(show_spinner=True, ttl=cache_timer_today)
def load_live_locations(home_name, min_id, max_id) -> pd.DataFrame:
    df = etl_processor.read_tvf(
        st.session_state["user_context"],   # user_context
        "call_bell",                        # schema
        "fn_report_app_live_locations",      # fn_name
        2 ,                                 # 2 = Home Level   
        home_name,                          # @home_name (VARCHAR(256) or None)
        # min_id,                             # @imin_seq_id INT first event record
        # max_id                              # @max_seq_id INT
    )
    return df

@st.cache_data(show_spinner=True, ttl=cache_timer_today)
def load_locations(parent, min_id, max_id) -> pd.DataFrame:
    df = etl_processor.read_tvf(
        st.session_state["user_context"],   # user_context
        "call_bell",                        # schema
        "fn_report_app_list_home_rooms",    # fn_name
        parent,                             # @home_name (VARCHAR(256) or None)
        min_id,                             # @imin_seq_id INT first event record
        max_id                              # @max_seq_id INT
    )
    return df

@st.cache_data(show_spinner=True, ttl=cache_timer_today)
def load_room_metrics(parent, min_id, max_id) -> pd.DataFrame:
    df = etl_processor.read_tvf(
        st.session_state["user_context"],   # user_context
        "call_bell",                        # schema
        "fn_report_app_room_metrics",       # fn_name
        parent,                             # @home_name (VARCHAR(256) or None)
        min_id,                             # @imin_seq_id INT first event record
        max_id                              # @max_seq_id INT
    )
    return df

@st.cache_data(show_spinner=True, ttl=cache_timer_today)
def load_datalogs(parent, child, min_id, max_id) -> pd.DataFrame:
    df = etl_processor.read_tvf(
        st.session_state["user_context"],   # user_context
        "call_bell",                        # schema
        "fn_report_app_room_datalog",       # fn_name
        child,  
        parent,                              # @home_name (VARCHAR(256) or None)
        max_id,                              # @max_seq_id INT
        min_id                              # @imin_seq_id INT first event record
    )
    return df
