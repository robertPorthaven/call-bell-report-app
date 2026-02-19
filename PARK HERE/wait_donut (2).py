# helper/wait_donut.py
from __future__ import annotations
import math
import streamlit as st

AMBER = "#f09c2e"
OCEAN = "#3e6f86"
SLATE = "#757a6e"
STONE = "#b5b5aa"
CLOUD = "#ebebeb"


TEXT   = "#31333f"   # neutral dark — never alarming
RED    = "#ff0000"

MAX_SECONDS = 600    # 10 minutes = full circle


def _donut_svg(seconds: int, label: str, size: int = 150, sub_label: str = "avg wait") -> str:
    cx = cy = size / 2
    r  = size * 0.36
    sw = size * 0.12
    circumference = 2 * math.pi * r

    capped     = min(seconds, MAX_SECONDS)
    arc_length = (capped / MAX_SECONDS) * circumference
    arc_colour = RED if seconds >= MAX_SECONDS else AMBER

    if seconds >= MAX_SECONDS:
        arc_length = circumference

    fv = size * 0.18
    fl = size * 0.09

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{CLOUD}" stroke-width="{sw}"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{arc_colour}" stroke-width="{sw}"
        stroke-linecap="round"
        stroke-dasharray="{arc_length:.2f} {circumference:.2f}"
        transform="rotate(-90 {cx} {cy})"/>
      <text x="{cx}" y="{cy - fv * 0.15}" text-anchor="middle" dominant-baseline="middle"
        font-size="{fv:.1f}" font-weight="700" fill="{TEXT}" font-family="sans-serif">{label}</text>
      <text x="{cx}" y="{cy + fv * 0.75}" text-anchor="middle" dominant-baseline="middle"
        font-size="{fl:.1f}" fill="{SLATE}" font-family="sans-serif">{sub_label}</text>
    </svg>
    """


def _percent_svg(percent: float, colour: str, sub_label: str, size: int = 150) -> str:
    cx = cy = size / 2
    r  = size * 0.36
    sw = size * 0.12
    circumference = 2 * math.pi * r
    arc_length = (min(max(percent, 0), 100) / 100) * circumference
    fv = size * 0.18
    fl = size * 0.09

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{CLOUD}" stroke-width="{sw}"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{colour}" stroke-width="{sw}"
        stroke-linecap="round"
        stroke-dasharray="{arc_length:.2f} {circumference:.2f}"
        transform="rotate(-90 {cx} {cy})"/>
      <text x="{cx}" y="{cy - fv * 0.15}" text-anchor="middle" dominant-baseline="middle"
        font-size="{fv:.1f}" font-weight="700" fill="{TEXT}" font-family="sans-serif">{percent:.0f}%</text>
      <text x="{cx}" y="{cy + fv * 0.75}" text-anchor="middle" dominant-baseline="middle"
        font-size="{fl:.1f}" fill="{SLATE}" font-family="sans-serif">{sub_label}</text>
    </svg>
    """


def _ratio_svg(a: int, b: int, colour_a: str, colour_b: str, sub_label: str, size: int = 150) -> str:
    """Two-segment donut: a vs b fill the circle proportionally."""
    cx = cy = size / 2
    r  = size * 0.36
    sw = size * 0.12
    circumference = 2 * math.pi * r
    total  = (a + b) if (a + b) > 0 else 1
    arc_a  = (a / total) * circumference
    arc_b  = (b / total) * circumference
    pct    = f"{a / total * 100:.0f}%"
    fv = size * 0.18
    fl = size * 0.09
    rot_b  = -90 + (a / total) * 360

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{CLOUD}" stroke-width="{sw}"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{colour_a}" stroke-width="{sw}"
        stroke-linecap="butt"
        stroke-dasharray="{arc_a:.2f} {circumference:.2f}"
        transform="rotate(-90 {cx} {cy})"/>
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{colour_b}" stroke-width="{sw}"
        stroke-linecap="butt"
        stroke-dasharray="{arc_b:.2f} {circumference:.2f}"
        transform="rotate({rot_b:.2f} {cx} {cy})"/>
      <text x="{cx}" y="{cy - fv * 0.15}" text-anchor="middle" dominant-baseline="middle"
        font-size="{fv:.1f}" font-weight="700" fill="{TEXT}" font-family="sans-serif">{pct}</text>
      <text x="{cx}" y="{cy + fv * 0.75}" text-anchor="middle" dominant-baseline="middle"
        font-size="{fl:.1f}" fill="{SLATE}" font-family="sans-serif">{sub_label}</text>
    </svg>
    """
# --- LEFT-HAND START VARIANT (9 o'clock) ---

def _ratio_svg_LH(
    a: int,
    b: int,
    colour_a: str,
    colour_b: str,
    sub_label: str,
    size: int = 150,
) -> str:
    """
    Two-segment donut that *starts at the LEFT (9 o'clock)* and fills clockwise.
    Segment A is drawn first, then segment B. Visually, A grows from left side.
    API mirrors _ratio_svg.
    """
    import math

    cx = cy = size / 2
    r = size * 0.36
    sw = size * 0.12
    circumference = 2 * math.pi * r

    total = (a + b) if (a + b) > 0 else 1
    arc_a = (a / total) * circumference
    arc_b = (b / total) * circumference

    pct_text = f"{(a / total) * 100:.0f}%"

    fv = size * 0.18  # main value font size
    fl = size * 0.09  # sublabel font size

    # Start angle at 9 o'clock (left-hand side)
    # Streamlit/HTML SVG uses degrees; we rotate the arc by this center-based angle.
    start_deg = 180  # 0° is 3 o'clock; 90° is 6; 180° is 9; 270° is 12

    # The second segment begins where the first one ends.
    rot_b = start_deg + (a / total) * 360

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}">
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{CLOUD}" stroke-width="{sw}"/>
      <!-- Segment A (left-hand start, clockwise fill) -->
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{colour_a}" stroke-width="{sw}"
              stroke-linecap="butt"
              stroke-dasharray="{arc_a:.2f} {circumference:.2f}"
              transform="rotate({start_deg} {cx} {cy})"/>
      <!-- Segment B -->
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{colour_b}" stroke-width="{sw}"
              stroke-linecap="butt"
              stroke-dasharray="{arc_b:.2f} {circumference:.2f}"
              transform="rotate({rot_b:.2f} {cx} {cy})"/>
      <text x="{cx}" y="{cy - fv * 0.15}" text-anchor="middle" dominant-baseline="middle"
            font-size="{fv:.1f}" font-weight="700" fill="{TEXT}" font-family="sans-serif">{pct_text}</text>
      <text x="{cx}" y="{cy + fv * 0.75}" text-anchor="middle" dominant-baseline="middle"
            font-size="{fl:.1f}" fill="{SLATE}" font-family="sans-serif">{sub_label}</text>
    </svg>
    """

def _kpi_card_svg(
    heading: str,
    kpi1_label: str,
    kpi1_value: str,
    kpi2_label: str,
    kpi2_value: str,
    width: int = 320,
    height: int = 150,
    heading_colour: str = STONE,
    label_colour: str = SLATE,
    value_colour: str = TEXT,
) -> str:
    """A clean card SVG containing a heading and two KPI values."""
    pad       = width * 0.06
    col1_x    = width * 0.27
    col2_x    = width * 0.73

    f_head  = height * 0.19
    f_label = height * 0.11
    f_value = height * 0.30

    head_y  = height * 0.28
    label_y = height * 0.56
    value_y = height * 0.80

    return (
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<rect width="{width}" height="{height}" rx="10" ry="10" fill="white" stroke="{CLOUD}" stroke-width="1.5"/>'
        f'<text x="{pad}" y="{head_y:.1f}" font-size="{f_head:.1f}" font-weight="700" fill="{heading_colour}" font-family="sans-serif" dominant-baseline="middle">{heading}</text>'
        f'<text x="{col1_x:.1f}" y="{label_y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="{f_label:.1f}" fill="{label_colour}" font-family="sans-serif">{kpi1_label}</text>'
        f'<text x="{col1_x:.1f}" y="{value_y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="{f_value:.1f}" font-weight="700" fill="{value_colour}" font-family="sans-serif">{kpi1_value}</text>'
        f'<text x="{col2_x:.1f}" y="{label_y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="{f_label:.1f}" fill="{label_colour}" font-family="sans-serif">{kpi2_label}</text>'
        f'<text x="{col2_x:.1f}" y="{value_y:.1f}" text-anchor="middle" dominant-baseline="middle" font-size="{f_value:.1f}" font-weight="700" fill="{value_colour}" font-family="sans-serif">{kpi2_value}</text>'
        f'</svg>'
    )


def render_kpi_card(
    heading: str,
    kpi1_label: str,
    kpi1_value: str | int,
    kpi2_label: str,
    kpi2_value: str | int,
    width: int = 320,
    height: int = 150,
    heading_colour: str = STONE,
    label_colour: str = SLATE,
    value_colour: str = TEXT,
) -> None:
    """Render a heading + two KPI values as a tidy card, matching the donut palette.

    Colour params default to the standard palette constants but can be overridden:
        heading_colour  – site/ward name  (default: STONE  #b5b5aa)
        label_colour    – "Total Calls"   (default: SLATE  #757a6e)
        value_colour    – "276"           (default: TEXT   #31333f)

    Uses a base64-encoded <img> tag so Streamlit's markdown parser cannot
    strip or re-flow the SVG text nodes.
    """
    import base64
    svg = _kpi_card_svg(
        heading, kpi1_label, str(kpi1_value), kpi2_label, str(kpi2_value),
        width, height, heading_colour, label_colour, value_colour,
    )
    b64 = base64.b64encode(svg.encode("utf-8")).decode("utf-8")
    st.markdown(
        f'<img src="data:image/svg+xml;base64,{b64}" width="{width}" height="{height}" style="display:block;"/>',
        unsafe_allow_html=True,
    )


def render_wait_donut(secs: int, text: str, size: int = 150, sub_label: str = "avg wait") -> None:
    st.markdown(_donut_svg(secs, text, size, sub_label), unsafe_allow_html=True)


def render_percent_donut(numerator: int, denominator: int, colour: str, sub_label: str, size: int = 150) -> None:
    percent = (numerator / denominator * 100) if denominator else 0
    st.markdown(_percent_svg(percent, colour, sub_label, size), unsafe_allow_html=True)


def render_ratio_donut(a: int, b: int, colour_a: str, colour_b: str, sub_label: str, size: int = 150) -> None:
    st.markdown(_ratio_svg(a, b, colour_a, colour_b, sub_label, size), unsafe_allow_html=True)
