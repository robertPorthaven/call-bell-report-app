# utils/aagrid_component.py
from pathlib import Path
import re
from st_aggrid import AgGrid, GridOptionsBuilder
import streamlit as st
from st_aggrid import JsCode

# Usage:
# render_call_grid(df_open_calls, "open_calls_grid", theme_color=AMBER )

# --- Brand colors ---
AMBER = "#f09c2e"
SLATE = "#757a6e"
OCEAN = "#3e6f86"

def load_aggrid_css(theme_color) -> dict[str, dict[str, str]]:
    css = Path("assets/aggrid.css").read_text(encoding="utf-8")
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.DOTALL)
    css = css.replace('--theme-color--', theme_color)  # Replace with actual amber color

    result: dict[str, dict[str, str]] = {}
    for match in re.finditer(r'([^{]+)\{([^}]+)\}', css):
        selector = match.group(1).strip()
        body = match.group(2).strip()
        props: dict[str, str] = {}
        for line in body.splitlines():
            line = line.strip().rstrip(';')
            if ':' in line:
                prop, _, val = line.partition(':')
                props[prop.strip()] = val.strip() + ' !important'
        if props:
            result[selector] = props

    return result

def load_pill_renderer() -> JsCode:
    return JsCode("""
    (function() {
        function PillRenderer() {}

        PillRenderer.prototype.init = function(params) {
            this.eGui = document.createElement('img');
            this.eGui.src = params.value || '';
            this.eGui.style.cssText = 'height:100%; object-fit:none; object-position:left center;';
        };

        PillRenderer.prototype.getGui    = function() { return this.eGui; };
        PillRenderer.prototype.refresh   = function() { return false; };
        PillRenderer.prototype.destroy   = function() {};

        return PillRenderer;
    })()
    """)

def render_call_grid(df_in, unique_key, theme_color= SLATE):
    """
    Reusable grid component based on the original working amber style.
    """
    if df_in.empty:
        st.info("No data available.")
        return
    df= df_in.copy()  # Avoid mutating original
    
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    
    if "Events" in df.columns:
        gb.configure_column("Room Location", filter=True, minWidth=150)
        gb.configure_column("Call Type", filter=True, minWidth=150)
        gb.configure_column("Start", filter=True, minWidth=150)        
        gb.configure_column("Events", cellRenderer=load_pill_renderer(), minWidth=350)

    # Use original sizing logic
    ROW_HEIGHT, HEADER_HEIGHT, GRID_CHROME = 48, 48, 10
    height = HEADER_HEIGHT + (len(df) * ROW_HEIGHT) + GRID_CHROME

    gb.configure_grid_options(
        enableCellTextSelection=True,
        domLayout='normal',
        suppressHorizontalScroll=True,
        rowHeight=ROW_HEIGHT,
        headerHeight=HEADER_HEIGHT,
    )

    AgGrid(
        df,
        gridOptions=gb.build(),
        custom_css=load_aggrid_css(theme_color),
        allow_unsafe_jscode=True,
        theme="alpine",
        height=height,
        key=unique_key, # Key is required for multiple grids on one page
        fit_columns_on_grid_load=True,
    )