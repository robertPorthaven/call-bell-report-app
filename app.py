# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Call Bell Dashboard – Streamlit entry point.
#
# This file is intentionally thin: it wires config → auth → db together and
# owns only the Streamlit UI.  All SQL / token logic lives in auth/ and db/.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
from datetime import datetime
import pandas as pd
import streamlit as st
import config
from utils.auth.token_provider import get_token_provider
from utils.aagrid_dataframe import render_call_grid
from utils.components import render_event_pills

# Define your color variables
AMBER = "#f09c2e"
OCEAN = "#3e6f86"
SLATE = "#757a6e"

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
    missing = [k for k, v in config.REQUIRED_VARS.items() if not v]
    if missing:
        st.error(f"🚨 Missing environment variables: {', '.join(missing)}")
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

@st.cache_data(show_spinner=True, ttl=5)
def load_open_calls(hours: int = 24) -> tuple[pd.DataFrame, datetime]:
    q = f"SELECT*FROM[call_bell].[fn_report_app_open_events](2,'Elizabeth Gardens')"
    df = st.session_state.sql_client.run_query(q)
    return df, datetime.now()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

try:
    _validate_env()

    if "sql_client" not in st.session_state:
        token_provider = get_token_provider(
            config.AZURE_CLIENT_ID,
            config.AZURE_CLIENT_SECRET,
            config.AZURE_TENANT_ID,
        )
        st.session_state.sql_client = config.SQL_BACKEND(
            config.SQL_SERVER,
            config.SQL_DATABASE,
            token_provider,
        )

    st.title("Call Bell – 24‑hour Summary")

    df, updated_at = load_open_calls(24)
    st.caption(f"Refreshed: {updated_at:%d/%m/%y %H:%M:%S}")
    st.subheader("Active Open Calls")
    # Convert event data to colour coded svgs and then draw the Open Call table
    df_open_calls = df[["Room Location","Call Type","Start","Total Time","Waiting Time","Care Time","Events"]]
    df_open_calls["Events"] = render_event_pills(df["Events"]) 

    render_call_grid(df_open_calls, "open_calls_grid", theme_color=AMBER, )


except Exception as exc:
    _fatal_page(exc)
