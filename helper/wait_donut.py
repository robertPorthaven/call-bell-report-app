# helper/wait_donut.py
from __future__ import annotations
import math
import streamlit as st

AMBER  = "#f09c2e"
RED    = "#ff0000"
SLATE  = "#757a6e"
TRACK  = "#e8e8e8"
TEXT   = "#31333f"   # neutral dark — never alarming

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
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="{sw}"/>
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
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="{sw}"/>
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
      <circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{TRACK}" stroke-width="{sw}"/>
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


def render_wait_donut(secs: int, text: str, size: int = 150, sub_label: str = "avg wait") -> None:
    st.markdown(_donut_svg(secs, text, size, sub_label), unsafe_allow_html=True)


def render_percent_donut(numerator: int, denominator: int, colour: str, sub_label: str, size: int = 150) -> None:
    percent = (numerator / denominator * 100) if denominator else 0
    st.markdown(_percent_svg(percent, colour, sub_label, size), unsafe_allow_html=True)


def render_ratio_donut(a: int, b: int, colour_a: str, colour_b: str, sub_label: str, size: int = 150) -> None:
    st.markdown(_ratio_svg(a, b, colour_a, colour_b, sub_label, size), unsafe_allow_html=True)