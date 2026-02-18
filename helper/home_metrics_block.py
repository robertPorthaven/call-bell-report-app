# helper/home_metrics_block.py
from __future__ import annotations
import pandas as pd
import streamlit as st
import altair as alt
from datetime import datetime
from helper.wait_donut import render_wait_donut, render_percent_donut, render_ratio_donut

OCEAN  = "#3e6f86"
SLATE  = "#757a6e"
AMBER  = "#f09c2e"
PURPLE = "#8e44ad"
RED    = "#ff0000"

CALL_TYPE_CHART = [
    ("total_calls",      "Calls",         AMBER),
    ("total_emergency",  "Emergency",     RED),
    ("total_present",    "Present",       SLATE),
    ("total_assistance", "Assistance",    OCEAN),
    ("total_anomaly",    "Anomaly/Fault", PURPLE),
]


def render_home_metrics_block(
    df_home_kpis: pd.DataFrame,
    selected_home: str,
    report_start: datetime,
    report_end: datetime,
) -> None:

    df_home = df_home_kpis[df_home_kpis["Home Name"] == selected_home]
    if df_home.empty:
        st.warning(f"No metrics found for **{selected_home}**.")
        return

    row = df_home.iloc[0]

    with st.container(border=True):

        # Outer layout: [left panel | avg wait | long wait | % present | % priority | care/wait | bar chart]
        left, c3, c4, c5, c6, c7, c8 = st.columns([2, 1, 1, 1, 1, 1, 2])

        # ── Left panel: home name top, metrics below ──────────────────────────
        with left:
            st.markdown(
                f"""
                <div style="line-height:1.5; margin-bottom:8px;">
                    <span style="font-size:1.15rem; font-weight:600; color:{OCEAN};">{selected_home}</span><br>

                </div>
                """,
                unsafe_allow_html=True,
            )
            m1, m2 = st.columns(2)
            m1.metric("Total Calls",     row["total_calls"])
            m2.metric("Total Emergency", row["total_emergency"])

        # ── Group 2 — wait times ──────────────────────────────────────────────
        with c3:
            render_wait_donut(int(row["avg_wait_secs"]), str(row["avg_wait_text"]), sub_label="avg wait")
        with c4:
            render_wait_donut(int(row["long_wait"]), str(row["long_wait_text"]), sub_label="longest wait")

        # ── Group 3 — call mix ────────────────────────────────────────────────
        with c5:
            render_percent_donut(int(row["total_present"]),    int(row["total_calls"]), SLATE, "% present")
        with c6:
            render_percent_donut(int(row["total_assistance"]), int(row["total_calls"]), AMBER, "% priority")

        # ── Group 4 — care vs wait ratio ──────────────────────────────────────
        with c7:
            render_ratio_donut(
                int(row["total_care"]),
                int(row["total_wait"]),
                SLATE, AMBER,
                "care / wait",
            )

        # ── Group 5 — bar chart breakdown ─────────────────────────────────────
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
                tooltip=["label:N", "count:Q"],
            )
            .properties(height=150)
            .configure_view(strokeWidth=0)
            .configure_axis(domainColor=SLATE)
        )

        with c8:
            st.altair_chart(chart, use_container_width=True)