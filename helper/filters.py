
# filters.py (standalone copy of components/filters.py)
from __future__ import annotations
from datetime import datetime, timedelta, time
from typing import List, Tuple
import streamlit as st

_DEF_WINDOW_HOURS = 24

def _hourly_quick_options(now: datetime) -> List[Tuple[str, datetime]]:
    options: List[Tuple[str, datetime]] = []
    options.append((f"Now ({now:%H:%M})", now))
    curr_hour = now.replace(minute=0, second=0, microsecond=0)
    for h in range(0, 48):
        dt = curr_hour - timedelta(hours=h)
        if dt.date() == now.date():
            label = f"Today {dt:%H}:00"
        elif dt.date() == (now.date() - timedelta(days=1)):
            label = f"Yesterday {dt:%H}:00"
        else:
            label = dt.strftime("%d %b %Y %H:00")
        options.append((label, dt))
    return options


def render_filters_form(home_names: list[str], logo_path: str | None = None) -> None:
    with st.sidebar:
        if logo_path:
            try:
                st.image(logo_path, use_container_width=True)
            except Exception:
                pass
        st.header("Filters")
        curr = st.session_state["filters"]
        curr_home = curr["home"]
        st.selectbox(
            "Home",
            home_names,
            index=home_names.index(curr_home) if curr_home in home_names else 0,
            key="home_select",
            on_change=lambda: st.session_state["filters"].__setitem__("home", st.session_state["home_select"]),
        )
        st.markdown("---")
        st.subheader("Date Picker")
        start_dt = st.session_state["filters"]["start"]
        end_dt = st.session_state["filters"]["end"]
        default_range = (start_dt.date(), end_dt.date())
        with st.form("date_range_form", clear_on_submit=False):
            picked = st.date_input("Date range", value=default_range)
            apply_dates = st.form_submit_button("Apply dates", use_container_width=True)
        if apply_dates:
            if isinstance(picked, tuple) and len(picked) == 2:
                d_start, d_end = picked
            else:
                d_start = picked
                d_end = picked
            new_start = datetime.combine(d_start, time.min)
            new_end = datetime.combine(d_end, time.max)
            st.session_state["filters"]["start"] = new_start
            st.session_state["filters"]["end"] = new_end
            st.rerun()
        st.caption("Tip: Pick any single day or a multi-day range. Times are set to the day boundaries.")
        st.markdown("---")
        st.subheader("Today Picker")
        now = datetime.now()
        opts = _hourly_quick_options(now)
        labels = [label for label, _ in opts]
        label_to_dt = {label: dt for label, dt in opts}
        if "_quick_label" not in st.session_state:
            st.session_state["_quick_label"] = labels[0]
        with st.form("today_quick_form", clear_on_submit=False):
            chosen_label = st.selectbox(
                "End time (last 24h ending at)",
                options=labels,
                index=labels.index(st.session_state["_quick_label"]) if st.session_state["_quick_label"] in labels else 0,
            )
            apply_quick = st.form_submit_button("Apply quick pick", use_container_width=True)
        if apply_quick:
            end_choice = label_to_dt[chosen_label]
            start_choice = end_choice - timedelta(hours=_DEF_WINDOW_HOURS)
            st.session_state["_quick_label"] = chosen_label
            st.session_state["filters"]["start"] = start_choice
            st.session_state["filters"]["end"] = end_choice
            st.rerun()
