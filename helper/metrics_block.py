# helper/home_metrics_block.py
from __future__ import annotations
import pandas as pd
import streamlit as st
import altair as alt
from helper.wait_donut import render_wait_donut, render_ratio_donut, render_kpi_card
from helper.data_loader import load_datalogs
from helper.aagrid_dataframe import render_call_grid


AMBER = "#f09c2e"
AMBER = "#f09c2e"
OCEAN = "#3e6f86"
SLATE = "#757a6e"
STONE = "#b5b5aa"
CLOUD = "#ebebeb"

PURPLE = "#8e44ad"
RED    = "#ff0000"

CALL_TYPE_CHART = [
    ("total_calls",      "Calls",         AMBER),
    ("total_emergency",  "Emergency",     RED),
    ("total_present",    "Present",       OCEAN),
    ("total_assistance", "Assistance",    SLATE),
    ("total_anomaly",    "Anomaly",      "#000000"),
]

CALL_CARE_LESS_CHART = [
    ("call_present_count",  "ATTENDED",     OCEAN),
    ("total_calls",      "Calls",         STONE),
    ("call_priority_count",    "PRIORITY",      AMBER),
]

def bordered_container(color: str = STONE, radius: str = "12px", thickness: str = "6px"):
    marker_id = f"m{color.strip('#')}"
    c = st.container()
    with c:
        st.markdown(# background color ⬇️ is a few line down when you have time.
            f"""
            <style>
                div[data-testid="stVerticalBlock"]:has(
                    > div[data-testid="stElementContainer"]
                    > div[data-testid="stMarkdown"]
                    > div
                    > div
                    > div#{marker_id}
                ) {{
                    border: {thickness} solid {color} !important;
                    border-radius: {radius} !important;
                    padding: 1rem !important;
                    background-color: CLOUD;                           
                }}
            </style>
            <div id="{marker_id}"></div>
            """,
            unsafe_allow_html=True,
        )
    return c

def render_metrics_block(df_kpis: pd.DataFrame, location: str, selected_home: str, min_seq_id: int, max_seq_id: int, color: str  = STONE ) -> None:

    row = df_kpis.iloc[0]

    with bordered_container(color = color):
        # Outer layout: [left panel | avg wait | long wait | % present | % priority | care/wait | bar chart]
        left, c2, c3, c4, c5, c6,  = st.columns([2, 1, 1, 1,  1, 3])

        ##### SSSSHHHHHHHhhhhh _some_one_ dropped an expander
        # with st.expander("Datalog"):
        #     dataflogs = load_datalogs( selected_home, location , min_seq_id, max_seq_id)
        #     st.dataframe(dataflogs)

        # ── Left panel: home name CALL EMERGENCY metrics below ──────────────────────────
        with left:
            render_kpi_card(
                heading= location ,
                kpi1_label="Total Calls",  kpi1_value= row["total_calls"],
                kpi2_label="Total Emergency", kpi2_value= row["total_emergency"],
                width=320, height=150,   # optional – defaults match donut height
                heading_colour = 'color'
            )
        # ── Call Care  vs Priority ──────────────────────────────────────
            df_col = (
                pd.DataFrame(
                    [{"label": label, 
                    "count": int(row[col]), "colour": colour}
                    for col, label, colour in CALL_CARE_LESS_CHART]
                )
                .sort_values("label", ascending=True)
            )
            chart = (
                alt.Chart(df_col)
                .mark_bar()
                .encode(
                    x=alt.X("label:N", axis=alt.Axis(labelColor=SLATE, title=None)),
                    y=alt.Y("count:Q", axis=alt.Axis(labels=False, ticks=False, grid=False, title=None)),
                    color=alt.Color("colour:N", scale=None, legend=None),
                )
                .properties(height=150)
                .configure_view(strokeWidth=0)
                .configure_axis(domainColor=SLATE)
            )  
        with c2:
            st.altair_chart(chart, width='stretch')   

        # ── Group 1 — CALL Care - PRESENT Less - PRIORITY ────────────────────
        with c3:
            render_wait_donut(int(row["avg_wait_secs"]), str(row["avg_wait_text"]), sub_label="avg wait")
        with c4:
            render_wait_donut(int(row["long_wait"]), str(row["long_wait_text"]), sub_label="long wait")

        # ── Group 4 — care vs wait ratio ──────────────────────────────────────
        # with c5:
        #     st.bar_chart(source, x="year", y="yield", color="site", stack=False)

        with c5:
            render_ratio_donut(
                int(row["total_care"]),
                int(row["total_wait"]),
                SLATE, AMBER,
                "care / wait",
            )

                                 
                # ── Group 3 — call mix ────────────────────────────────────────────────
        df_bar = (
            pd.DataFrame(
                [{"label": label, "count": int(row[col]), "colour": colour}
                 for col, label, colour in CALL_TYPE_CHART]
            )
            .sort_values("count", ascending=True)
        )

        chart = (
            alt.Chart(df_bar)
            .mark_bar()
            .encode(
                x=alt.X("count:Q", axis=alt.Axis(labels=False, ticks=False, grid=False, title=None)),
                y=alt.Y("label:N", sort=None, axis=alt.Axis(labelColor=SLATE, title=None)),
                color=alt.Color("colour:N", scale=None, legend=None),
                tooltip=[
                    alt.Tooltip("label:N", title="Event Type"), # Custom title here
                    alt.Tooltip("count:Q", title="Count")
                    ],
            )
            .properties(height=150)
            .configure_view(strokeWidth=0)
            .configure_axis(domainColor=SLATE)
        )

        with c6:
            st.altair_chart(chart, width='stretch')





    