
# app_refactored.py — Call Bell Dashboard (Variant B: Sidebar filters)
from __future__ import annotations
import json
from datetime import datetime, timedelta
import streamlit as st

from helper.aagrid_dataframe import render_call_grid
from helper.aggrid_pill_svg import render_event_pills_svgs
from helper.data_loader import (
    validate_env,
    load_home_metrics,
    load_live_locations,
    load_homes,
    load_room_metrics,
)
from helper.metrics_block import render_metrics_block

from components.filters import render_filters_form

SLATE = "#757a6e"
AMBER = "#f09c2e"
OCEAN = "#3e6f86"
STONE = "#b5b5aa"
CLOUD = "#ebebeb"

# ──────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG + CSS
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Call Bell Report",
    page_icon="assets/image.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Load custom CSS if present
try:
    with open("assets/style.css", "r", encoding="utf-8") as css_file:
        st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)
except FileNotFoundError:
    pass

# ──────────────────────────────────────────────────────────────────────────────
# GLOBAL ERROR PAGE
# ──────────────────────────────────────────────────────────────────────────────

def _fatal_page(exc: Exception) -> None:
    timestamp = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    st.markdown(f"### 🚨 System Error 
**Time of failure:** {timestamp}")
    st.exception(exc)
    st.stop()

# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────
try:
    # — Title and refresh slot
    st.title("Call Bell Report", anchor=False)
    refreshed_slot = st.empty()

    # — SECTION: Filters in sidebar
    validate_env()
    df_home_names = load_homes()
    home_names = sorted(df_home_names["Home Name"].dropna().unique().tolist())
    if not home_names:
        st.warning("No home data available for the selected period.")
        st.stop()

    default_end = datetime.now()
    default_start = default_end - timedelta(hours=24)

    if "filters" not in st.session_state:
        st.session_state["filters"] = {
            "home": home_names[0],
            "start": default_start,
            "end": default_end,
        }

    # Render the sidebar filters with optional logo
    render_filters_form(home_names, logo_path="assets/image.png")

    selected_home = st.session_state["filters"]["home"]
    report_start = st.session_state["filters"]["start"]
    report_end = st.session_state["filters"]["end"]

    # — SECTION: Home KPIs
    with st.container():
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        df_home_kpis, updated_at = load_home_metrics(report_start, report_end, selected_home)
        refreshed_slot.markdown(f"###### Refreshed: {updated_at:%d/%m/%y %H:%M:%S}")
        render_metrics_block(df_home_kpis, selected_home, SLATE)  # type: ignore
        row = df_home_kpis[df_home_kpis["Home Name"] == selected_home].iloc[0]
        min_seq_id = int(row["min_seq_id"])
        max_seq_id = int(row["max_seq_id"])
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    # — SECTION: Live Locations
    st.markdown("### Live Locations — (Not Reset)")
    with st.container():
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        df_active = load_live_locations(selected_home, min_seq_id, max_seq_id)
        df_active.loc[:, "Events"] = render_event_pills_svgs(df_active["Events"])  # type: ignore
        df_active["Events"] = df_active["Events"].apply(json.dumps)
        render_call_grid(df_active, "open_calls_grid", theme_color=AMBER)
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

    # — SECTION: Room History
    st.markdown("### Room History")
    with st.container():
        st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)
        df_room_kpis = load_room_metrics(selected_home, min_seq_id, max_seq_id)  # type: ignore
        st.caption("Rooms with no event are not shown.")
        for i in range(len(df_room_kpis)):
            row_df = df_room_kpis.iloc[[i]]
            room = str(row_df.iloc[0, 0])
            render_metrics_block(row_df, room, OCEAN)
            st.markdown('<div style="height:0.5rem"></div>', unsafe_allow_html=True)

except Exception as exc:
    _fatal_page(exc)
