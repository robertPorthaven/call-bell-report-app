# utils/altair_component.py
import altair as alt
import pandas as pd
import streamlit as st
import numpy as np

# Usage
# kpi_card("Total Call", 12842, delta=0.042)
# double_arc_chart("Avg Wait", 0.65, "Long Wait", 0.25)
# gauge_chart("Wait/Care Hours Ratio", 0.37)
# donut_chart("Calls Present %", 0.72)
# donut_chart("Calls Priority %", 0.72)
# kpi_card("Total Emergency", 12842, delta=0.042)
# df_types = pd.DataFrame({"Call-Type":["Call","Emergency","Present","Assistance","Anomaly/Fault"], "Count":[320, 210, 55, 3, 160000]})
# horizontal_bars(df_types, "Source", "Count")

def donut_chart(label: str, value: float):
    # value in [0,1]
    df = pd.DataFrame({"label": [label, "Remaining"], "value": [value, 1 - value]})
    chart = alt.Chart(df).mark_arc(innerRadius=60).encode(
        theta="value:Q",
        color=alt.Color("label:N", scale=alt.Scale(range=["#f09c2e", "#e9ecef"]), legend=None),
        tooltip=["label:N", alt.Tooltip("value:Q", format=".0%")]
    ).properties(width=220, height=220)
    st.altair_chart(chart, use_container_width=False)

def double_arc_chart(center_label: str, center_value: float, outer_label: str, outer_value: float):
    base = pd.DataFrame({
        "ring": [center_label, "Center Remaining", outer_label, "Outer Remaining"],
        "value": [center_value, 1 - center_value, outer_value, 1 - outer_value],
        "layer": ["center","center","outer","outer"]
    })
    color_map = alt.Scale(domain=[center_label, "Center Remaining", outer_label, "Outer Remaining"],
                          range=["#f09c2e", "#e9ecef", "#7f56d9", "#e9ecef"])
    center = alt.Chart(base[base["layer"]=="center"]).mark_arc(innerRadius=40, outerRadius=70).encode(
        theta="value:Q",
        color=alt.Color("ring:N", scale=color_map, legend=None),
        tooltip=["ring:N", alt.Tooltip("value:Q", format=".0%")]
    )
    outer = alt.Chart(base[base["layer"]=="outer"]).mark_arc(innerRadius=75, outerRadius=105).encode(
        theta="value:Q",
        color=alt.Color("ring:N", scale=color_map, legend=None),
        tooltip=["ring:N", alt.Tooltip("value:Q", format=".0%")]
    )
    st.altair_chart(center + outer, use_container_width=False)

def gauge_chart(label: str, value: float):  # value in [0,1]
    # Background semicircle + filled value
    bg = pd.DataFrame({"start":[0], "end":[np.pi]})
    fg = pd.DataFrame({"start":[0], "end":[value*np.pi]})

    def arc(df, color):
        return alt.Chart(df).transform_calculate(
            theta="datum.start + (datum.end - datum.start) * datum.t"
        ).transform_fold(["t"], as_=["t", "v"]).mark_arc(innerRadius=60, outerRadius=90).encode(
            theta=alt.Theta("end:Q", stack=None),
            color=alt.value(color)
        ).properties(width=260, height=160)

    # Simpler: use theta on value directly
    bg2 = alt.Chart(pd.DataFrame({"value":[1]})).mark_arc(innerRadius=60, outerRadius=90).encode(
        theta=alt.Theta("value:Q", stack=None),
        color=alt.value("#e9ecef")
    )
    fg2 = alt.Chart(pd.DataFrame({"value":[value]})).mark_arc(innerRadius=60, outerRadius=90).encode(
        theta=alt.Theta("value:Q", stack=None),
        color=alt.value("#f09c2e"),
        tooltip=[alt.Tooltip("value:Q", title=label, format=".0%")]
    )
    st.altair_chart((bg2 + fg2).properties(title=label), use_container_width=False)

def kpi_card(label: str, value: int, delta: float | None = None):
    st.metric(label=label, value=f"{value:,}", delta=None if delta is None else f"{delta:+.1%}")

def horizontal_bars(df: pd.DataFrame, category_col: str, value_col: str):
    chart = alt.Chart(df).mark_bar(color="#7f56d9").encode(
        y=alt.Y(f"{category_col}:N", sort="-x", title=category_col),
        x=alt.X(f"{value_col}:Q", title=value_col),
        tooltip=[category_col, value_col]
    ).properties(height=alt.Step(26))
    st.altair_chart(chart, use_container_width=True)

