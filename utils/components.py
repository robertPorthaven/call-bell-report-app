# utils/components.py
from st_aggrid import AgGrid, GridOptionsBuilder
import streamlit as st
from utils.aggrid_loader import load_aggrid_css, load_pill_renderer

def render_call_grid(df, unique_key, theme_color="#757a6e"):
    """
    Reusable grid component based on the original working amber style.
    """
    if df.empty:
        st.info("No data available.")
        return

    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(resizable=True, sortable=True, filter=False)
    
    if "Events" in df.columns:
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