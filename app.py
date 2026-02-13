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
from auth.token_provider import get_token_provider

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG  (must be the first Streamlit call)
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Call Bell Dashboard",
    page_icon="assets/image.png",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────────────────────
# EXTERNAL CSS
# ─────────────────────────────────────────────────────────────────────────────

def _load_css(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            st.markdown(f"<style>{fh.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass  # non-fatal

_load_css("assets/style.css")

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
# FORMATTING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_TIME_COLS = {"waiting time", "care time", "total time", "emergency time"}

def format_seconds(seconds) -> str:
    if pd.isna(seconds):
        return ""
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def is_time_column(col: str) -> bool:
    return col.strip().lower() in _TIME_COLS

# ─────────────────────────────────────────────────────────────────────────────
# DATA LOADING
# ─────────────────────────────────────────────────────────────────────────────

@st.cache_data(show_spinner=True, ttl=15)
def load_data(hours: int = 24) -> tuple[pd.DataFrame, datetime]:
    q = f"SELECT * FROM [call_bell].[fn_report_app_data]({int(hours)})"
    df = st.session_state.sql_client.run_query(q)
    return df, datetime.now()

# ─────────────────────────────────────────────────────────────────────────────
# UI SECTIONS
# ─────────────────────────────────────────────────────────────────────────────

def _render_open_calls(df: pd.DataFrame, home_name: str) -> None:
    st.subheader(f"{home_name} – Active Open Calls (Not Reset)")

    if "Call Type" not in df.columns:
        st.write("No OPEN calls.")
        return

    open_df = (
        df[df["Call Type"].astype(str).str.contains("OPEN", case=False, na=False)]
        .sort_values("Start Time")
        .copy()
    )

    if open_df.empty:
        st.write("No OPEN calls.")
        return

    open_df = open_df.drop(columns=["HomeName", "Emergency Time"], errors="ignore")
    for col in open_df.columns:
        if is_time_column(col):
            open_df[col] = open_df[col].map(format_seconds)
    if "Start Date" in open_df.columns:
        open_df["Start Date"] = (
            pd.to_datetime(open_df["Start Date"], errors="coerce")
            .dt.strftime("%d/%m/%Y %H:%M:%S")
        )
    st.dataframe(open_df, width='stretch', hide_index=True)


def _render_room_summary(df: pd.DataFrame) -> None:
    st.divider()
    st.subheader("Room Summary (last 24 hours)")

    # ── Normalise seconds columns ──
    col_map = {
        "Waiting Time": "WaitingSeconds",
        "Care Time": "CareSeconds",
        "Total Time": "TotalSeconds",
        "Emergency Time": "EmergencySeconds",
    }
    for src, dst in col_map.items():
        df[dst] = df[src] if src in df.columns else 0

    for key in ["HomeName", "Room Location"]:
        df[key] = df.get(key, pd.Series(dtype=str)).fillna("Unknown")

    group_keys = ["HomeName", "Room Location"]

    def pct95(s: pd.Series) -> int:
        return int(s.quantile(0.95)) if len(s) else 0

    agg_df = (
        df.groupby(group_keys, dropna=False)
        .agg(
            EventCount=("WaitingSeconds", "size"),
            TotalWaiting=("WaitingSeconds", "sum"),
            AvgWaiting=("WaitingSeconds", "mean"),
            P95Waiting=("WaitingSeconds", pct95),
            TotalCare=("CareSeconds", "sum"),
            TotalEmergency=("EmergencySeconds", "sum"),
            LastEvent=("Start Time", "max") if "Start Time" in df.columns
                      else ("WaitingSeconds", "size"),
        )
        .reset_index()
    )

    # ── Call-type counts per room ──
    call_type_dict: dict[tuple, dict] = {}
    if "Call Type" in df.columns:
        for _, r in (
            df.groupby(group_keys + ["Call Type"], dropna=False)
            .size()
            .rename("Count")
            .reset_index()
            .iterrows()
        ):
            key = (r["HomeName"], r["Room Location"])
            label = str(r["Call Type"]) if pd.notna(r["Call Type"]) else "Unknown"
            call_type_dict.setdefault(key, {})[label] = int(r["Count"])

    # ── Render: homes ordered by total events ──
    homes_order = (
        agg_df.groupby("HomeName", dropna=False)["EventCount"]
        .sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    for home in homes_order:
        home_block = (
            agg_df[agg_df["HomeName"] == home]
            .sort_values(["EventCount", "TotalWaiting"], ascending=[False, False])
        )
        for _, row in home_block.iterrows():
            room = row["Room Location"]
            key = (home, room)
            with st.container(border=True):
                st.markdown(f"**{home} - {room}** · {int(row['EventCount'])} events")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total Waiting Time",   format_seconds(row["TotalWaiting"]))
                c2.metric("Average Waiting Time", format_seconds(row["AvgWaiting"]))
                c3.metric("95% Waiting Time",     format_seconds(row["P95Waiting"]))
                c4.metric("Total Care Time",      format_seconds(row["TotalCare"]))
                c5.metric("Total Emergency Time", format_seconds(row["TotalEmergency"]))

                pairs = sorted(call_type_dict.get(key, {}).items(), key=lambda x: (-x[1], x[0]))
                for i in range(0, len(pairs), 6):
                    row_slice = pairs[i:i + 6]
                    for col, (label, count) in zip(st.columns(len(row_slice)), row_slice):
                        col.metric(label, str(count))

# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

try:
    _validate_env()

    # Initialise the SQL client once per session, using the selected backend.
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
    st.caption("Times are displayed as Hours:Minutes:Seconds")

    df, updated_at = load_data(24)

    if df is None or df.empty:
        st.info("No data found for the last 24 hours.")
        st.stop()

    st.caption(f"Refreshed: {updated_at:%d/%m/%y %H:%M:%S}")

    home_name = df.get("HomeName", pd.Series(dtype=str)).dropna().unique()
    home_name = home_name[0] if len(home_name) else "Home"

    _render_open_calls(df, home_name)
    _render_room_summary(df)

except Exception as exc:
    _fatal_page(exc)
