# app.py
# ─────────────────────────────────────────────────────────────────────────────
# Call Bell Dashboard – Streamlit entry point.
# ─────────────────────────────────────────────────────────────────────────────

from __future__ import annotations
import streamlit as st
from datetime import datetime, timedelta
from helper.aagrid_dataframe import render_call_grid
from helper.aggrid_pill_svg import render_event_pills_svgs
from helper.data_loader import load_home_metrics, validate_env #, load_open_calls
from helper.home_metrics_block import render_home_metrics_block

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
    st.markdown(f"<style>{css_file.read()}</style>", unsafe_allow_html=True)

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

        Please notify the data bunny 🐰
        > "Errors happen. Great dashboards handle them gracefully."
        """,
        unsafe_allow_html=True,
    )
    st.exception(exc)
    st.stop()

# ─────────────────────────────────────────────────────────────────────────────
# MAIN HEADER
# ─────────────────────────────────────────────────────────────────────────────
try:
    validate_env()

    st.title("Call Bell Report")

    # Default loads the last 24 hours of event data for all homes the user can see
    report_end = datetime.now()
    report_start = report_end - timedelta(hours=48)
    df_home_kpis, updated_at = load_home_metrics(report_start, report_end , 'ALL')
# ─────────────────────────────────────────────────────────────────────────────
# HOME SELECTOR
# ─────────────────────────────────────────────────────────────────────────────
    home_names = df_home_kpis["Home Name"].dropna().unique().tolist()

    if len(home_names) == 0:
        st.warning("No home data available for the selected period.")
        st.stop()

    elif len(home_names) == 1:
        selected_home = home_names[0]

    else:
        selected_home = st.selectbox(
            label='',
            options=sorted(home_names),
            index=0,
            key="selected_home",
        )
    st.caption(f"Refreshed: {updated_at:%d/%m/%y %H:%M:%S}")   
 
    render_home_metrics_block(df_home_kpis, selected_home, report_start, report_end) # type: ignore




# ─────────────────────────────────────────────────────────────────────────────
#  ACTIVE ROOMs
# ─────────────────────────────────────────────────────────────────────────────
    # df_active, _ = load_open_calls(24)
    # st.subheader("Active Room Locations - Not Reset")

    # df_active = df_active.loc[:, ["Room Location", "Call Type", "Start", "Total Time", "Waiting Time", "Care Time", "Events"]]
    
    # # Convert event data to colour coded svgs 
    # df_active.loc[:, "Events"] = render_event_pills_svgs(df_active["Events"])
    # df_active["Events"] = df_active["Events"].apply(json.dumps)

    # render_call_grid(df_active, "open_calls_grid", theme_color=AMBER, )






except Exception as exc:
    _fatal_page(exc)