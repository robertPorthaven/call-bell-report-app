# utils/components.py
import base64
import streamlit as st

# Usage:
# df['Events'] = render_event_pills(df['Events'])       #--> df with image data - noice

# --- Brand colors ---
AMBER = "#f09c2e"
SLATE = "#757a6e"
OCEAN = "#3e6f86"
STYLES = {
    "call":       {"bg": "#ffffff", "border": AMBER,     "fg": "#000000"},
    "priority":   {"bg": AMBER,     "border": AMBER,     "fg": "#ffffff"},
    "present":    {"bg": SLATE,     "border": SLATE,     "fg": "#ffffff"},
    "emergency":  {"bg": "#ff0000", "border": "#ff0000", "fg": "#ffffff"},
    "reset":      {"bg": "#ffffff", "border": SLATE,     "fg": "#000000"},
    "assistance": {"bg": OCEAN,     "border": SLATE,     "fg": "#ffffff"},
}
ANOMALY = {"bg": "#ffffff", "border": "#ff0000", "fg": "#ff0000"}

H       = 24
R       = H // 2          # full radius → stadium/pill shape
CHAR_W  = 8.5             # approximate px per character in Arial 12px
PADDING = 4               # horizontal padding
MIN_W   = 52
ARROW   = "\u27A4"
FONT_FAMILY = "Consolas, Menlo, Liberation Mono, ui-monospace, monospace"

@st.cache_data(show_spinner=False)
def _event_line(events: str) -> str:
    """Full event sequence → single composite SVG data URI."""
    labels = [x.strip() for x in str(events).upper().split(">") if x.strip()]
    if not labels:
        return ""

    # Collect per-pill widths
    pill_ws   = [max(MIN_W, int(len(lbl) * CHAR_W + PADDING)) for lbl in labels]
    arrow_w   = 16
    gap       = 0

    n         = len(labels)
    total_w   = sum(pill_ws) + (n - 1) * (arrow_w + gap * 2)
    CANVAS_W  = max(total_w, 360)   # left-align in dataframe

    parts = [
        f'<svg width="{CANVAS_W}" height="{H}" xmlns="http://www.w3.org/2000/svg"'
        f' xmlns:xlink="http://www.w3.org/1999/xlink">'
    ]

    x = 0
    for i, (lbl, w) in enumerate(zip(labels, pill_ws)):
        s = STYLES.get(lbl.lower(), ANOMALY)
        parts += [
            f'<rect x="{x+1}" y="1" width="{w-2}" height="{H-2}" rx="{R}" ry="{R}"'
            f' fill="{s["bg"]}" stroke="{s["border"]}" stroke-width="2"/>',
            f'<text x="{x + w//2}" y="{H//2}" dominant-baseline="middle"'
            f' text-anchor="middle" font-family="{FONT_FAMILY}"'
            f' font-size="12" font-weight="600" fill="{s["fg"]}">{lbl}</text>',
        ]
        x += w
        if i < n - 1:
            x += gap
            parts.append(
                f'<text x="{x + arrow_w//2}" y="{H//2}" dominant-baseline="middle"'
                f' text-anchor="middle" font-family="{FONT_FAMILY}"'
                f' font-size="10" fill="#3e6f86">{ARROW}</text>'
            )
            x += arrow_w + gap

    parts.append("</svg>")
    svg = "".join(parts)
    b64 = base64.b64encode(svg.encode()).decode()
    return f"data:image/svg+xml;base64,{b64}"


@st.cache_data(show_spinner=False)
def render_event_pills(series):
    """Transform df['Events'] → data-URI SVGs for both dataframe and AgGrid."""
    return series.apply(_event_line)