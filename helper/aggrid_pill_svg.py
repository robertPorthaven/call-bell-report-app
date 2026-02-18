# utils/components.py
import base64
import re
import streamlit as st

# --- Brand colors ---
AMBER = "#f09c2e"
SLATE = "#757a6e"
OCEAN = "#3e6f86"

STYLES = {
    "call":        {"bg": "#ffffff", "border": AMBER, "fg": "#000000"},
    "priority":    {"bg": AMBER,     "border": AMBER, "fg": "#ffffff"},
    "present":     {"bg": SLATE,     "border": SLATE, "fg": "#ffffff"},
    "emergency":   {"bg": "#ff0000", "border": "#ff0000", "fg": "#ffffff"},
    "reset":       {"bg": "#ffffff", "border": SLATE, "fg": "#000000"},
    "assistance":  {"bg": OCEAN,     "border": SLATE, "fg": "#ffffff"},
}
ANOMALY = {"bg": "#ffffff", "border": "#ff0000", "fg": "#ff0000"}

H = 24
R = H // 2
CHAR_W = 8.5
HPAD = 4
MIN_W = 52
FONT_FAMILY = "Consolas, Menlo, Liberation Mono, ui-monospace, monospace"


def _make_pill_svg(label: str) -> str:
    lbl = str(label).strip()
    if not lbl:
        return ""
    style = STYLES.get(lbl.lower(), ANOMALY)
    w = max(MIN_W, int(len(lbl) * CHAR_W + HPAD * 2))
    svg = (
        f'<svg width="{w}" height="{H}" xmlns="http://www.w3.org/2000/svg">'
        f'  <rect x="1" y="1" width="{w-2}" height="{H-2}" rx="{R}" ry="{R}" '
        f'        fill="{style["bg"]}" stroke="{style["border"]}" stroke-width="2"/>'
        f'  <text x="{w//2}" y="{H//2}" dominant-baseline="middle" text-anchor="middle" '
        f'        font-family="{FONT_FAMILY}" font-size="12" font-weight="600" '
        f'        fill="{style["fg"]}">{lbl.upper()}</text>'
        f'</svg>'
    )
    import base64 as _b64
    b64 = _b64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{b64}"


def _event_svgs_list(events: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\s*[>➤]\s*", str(events or "")) if p.strip()]
    return [_make_pill_svg(p) for p in parts]


@st.cache_data(show_spinner=False)
def render_event_pills_svgs(series):
    """
    Transform df['Events'] (string like 'A > B > C') -> list[data-URI] (one per pill).
    """
    return series.apply(_event_svgs_list)
