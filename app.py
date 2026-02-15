# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Call Bell Dashboard – Streamlit entry point.
#
# This file is intentionally thin: it wires config → auth → db together and
# owns only the Streamlit UI.  All SQL / token logic lives in auth/ and db/.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
from datetime import datetime
from st_aggrid import AgGrid, GridOptionsBuilder
import pandas as pd
import streamlit as st
import config
from auth.token_provider import get_token_provider
from utils.aggrid_loader import load_pill_renderer, load_aggrid_css
from utils.pills import render_event_pills

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
    q = f"SELECT * FROM [call_bell].[fn_report_app_data]({int(hours)})"
    df = st.session_state.sql_client.run_query(q)
    return df, datetime.now()

# ─────────────────────────────────────────────────────────────────────────────
# UI SECTIONS
# ─────────────────────────────────────────────────────────────────────────────
def _render_open_calls(open_df: pd.DataFrame) -> None:
    st.subheader(f"Active Open Calls")
    st.caption("Times are displayed as Hours:Minutes:Seconds")

    if open_df.empty:
        return st.info("No OPEN calls.") # type: ignore

    gb = GridOptionsBuilder.from_dataframe(open_df)
    gb.configure_default_column(resizable=True, sortable=True, filter=False)  # filter off by default
    gb.configure_column("Events", cellRenderer=load_pill_renderer(), minWidth=350)

    # Only enable filter on columns where it makes sense
    gb.configure_column("Room Location", filter=True)
    gb.configure_column("Call Type", filter=True)

    ROW_HEIGHT    = 48
    HEADER_HEIGHT = 48
    GRID_CHROME   = 10   # Extra space to prevent vertical scrollbar APPEARING
    height = HEADER_HEIGHT + (len(open_df) * ROW_HEIGHT) + GRID_CHROME

    gb.configure_grid_options(
        enableCellTextSelection=True,
        domLayout='normal',
        suppressHorizontalScroll=True,
        rowHeight=ROW_HEIGHT,
        headerHeight=HEADER_HEIGHT,
    )

    AgGrid(
        open_df,
        gridOptions=gb.build(),
        custom_css=load_aggrid_css(),
        allow_unsafe_jscode=True,
        theme="alpine",
        height=height,
        fit_columns_on_grid_load=True,
    )


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

    if df is None or df.empty:
        st.info("No data found for the last 24 hours.")
        st.stop()

    st.caption(f"Refreshed: {updated_at:%d/%m/%y %H:%M:%S}")
    df["Events"] = render_event_pills(df["Events"])
    _render_open_calls(df)

except Exception as exc:
    _fatal_page(exc)
