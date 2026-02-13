import os
from datetime import datetime
import streamlit as st
import pandas as pd

# Optional: load .env for local development
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # It's fine if python-dotenv isn't installed in prod
    pass

from obo_sql_client import OboSqlClient  # local module

# ───────────────────────────────────────────────────────────────
# 0) ENVIRONMENT VARIABLES + VALIDATION
# ───────────────────────────────────────────────────────────────

AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID")
SQL_SERVER = os.getenv("SQL_SERVER")
SQL_DATABASE = os.getenv("SQL_DATABASE")

def validate_env_and_stop_if_missing():
    """Show a friendly error if any required env var is missing."""
    required_vars = {
        "SQL_SERVER": SQL_SERVER,
        "SQL_DATABASE": SQL_DATABASE,
        "AZURE_CLIENT_ID": AZURE_CLIENT_ID,
        "AZURE_CLIENT_SECRET": AZURE_CLIENT_SECRET,
        "AZURE_TENANT_ID": AZURE_TENANT_ID,
    }
    missing = [k for k, v in required_vars.items() if not v]
    if missing:
        st.error(f"🚨 Missing environment variables: {', '.join(missing)}")
        st.info(
            "Tip: For local dev, create a `.env` file next to app.py and call `load_dotenv()`."
            " In Azure Container Apps, set these under **Application settings** "
            "(secrets + env vars)."
        )
        st.stop()

# ───────────────────────────────────────────────────────────────
# 1) PAGE CONFIG
# ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Call Bell Dashboard", page_icon="assets/image.png", layout="wide")

# ───────────────────────────────────────────────────────────────
# 2) LOAD EXTERNAL CSS
# ───────────────────────────────────────────────────────────────
def load_css(path: str) -> None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        # Non-fatal: continue without custom CSS
        pass

load_css("assets/style.css")

# ───────────────────────────────────────────────────────────────
# 3) GLOBAL ERROR PAGE
# ───────────────────────────────────────────────────────────────
def fatal_page(exc: Exception) -> None:
    timestamp = datetime.now().strftime("%d/%m/%y %H:%M:%S")
    st.markdown(
        f"""
        ### 🚨 System Error

        The application encountered a critical issue and cannot continue.  
        **Time of failure:** {timestamp}  
        Please notify the data bunny 🐰.  
        > “Errors happen. Great dashboards handle them gracefully.”
        """,
        unsafe_allow_html=True,
    )
    st.exception(exc)
    st.stop()

# ───────────────────────────────────────────────────────────────
# 4) TOKEN EXCHANGE HELPERS (OBO + Local fallback)
# ───────────────────────────────────────────────────────────────
import msal  # keep import local to fail fast if missing

SQL_SCOPE = ["https://database.windows.net//.default"]

def _new_confidential_client() -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=AZURE_CLIENT_ID,
        client_credential=AZURE_CLIENT_SECRET,
        authority=f"https://login.microsoftonline.com/{AZURE_TENANT_ID}",
    )

import base64, json

def _client_credentials_sql_token() -> dict:
    app = _new_confidential_client()
    result = app.acquire_token_for_client(scopes=SQL_SCOPE)
    if "access_token" not in result:  # type: ignore
        raise Exception(f"Client credential token failed: {result}")

    # --- ENHANCED IDENTITY DEBUG ---
    import base64, json
    payload = result["access_token"].split(".")[1] # type: ignore
    payload += "=" * (4 - len(payload) % 4)
    decoded = json.loads(base64.urlsafe_b64decode(payload))
    
    st.info(f"Checking Identity: {decoded.get('display_name', 'Service Principal')}")
    
    print("=== IDENTITY DATA FOR SQL ADMIN ===")
    print(f"App ID (client_id): {decoded.get('appid')}")
    print(f"Object ID (oid):    {decoded.get('oid')}")
    print(f"Display Name:       {decoded.get('display_name')}") # May be None for client_credentials
    print("====================================")
    # --- END DEBUG ---

    expires_on = datetime.now().timestamp() + result.get("expires_in", 0) # type: ignore
    return {"access_token": result["access_token"], "expires_on": expires_on} # type: ignore

def exchange_header_for_sql_token() -> dict:
    """
    If Easy Auth is present (Azure), do OBO using the user's token from headers.
    Otherwise (local), fall back to client credentials.
    Returns { access_token: str, expires_on: float(timestamp) }.
    """
    # Streamlit public API (1.54+): st.context.headers. Guard for older versions.
    headers = {}
    try:
        headers = getattr(st, "context", None).headers if getattr(st, "context", None) else {} # type: ignore
    except Exception:
        headers = {}

    user_access_token = (headers or {}).get("X-MS-TOKEN-AAD-ACCESS-TOKEN")
    if not user_access_token:
        # Local dev (no Easy Auth)
        return _client_credentials_sql_token()

    # OBO path (Azure with Easy Auth)
    app = _new_confidential_client()
    result = app.acquire_token_on_behalf_of(user_assertion=user_access_token, scopes=SQL_SCOPE)

    if "access_token" not in result:
        raise Exception(f"OBO failed: {result.get('error')} - {result.get('error_description')}")

    expires_on = datetime.now().timestamp() + result.get("expires_in", 0)
    return {"access_token": result["access_token"], "expires_on": expires_on}

# ───────────────────────────────────────────────────────────────
# 5) MAIN APP (single global try/except)
# ───────────────────────────────────────────────────────────────
try:
    validate_env_and_stop_if_missing()

    # -----------------------------------------------------------
    # CONFIG + DATA ACCESS
    # -----------------------------------------------------------
    if "sql_user_client" not in st.session_state:
        st.session_state.sql_user_client = OboSqlClient(
            SQL_SERVER, SQL_DATABASE, exchange_header_for_sql_token # type: ignore
        )

    @st.cache_data(show_spinner=True, ttl=15)
    def load_data(hours: int = 24) -> tuple[pd.DataFrame, datetime]:
        """Load data from SQL and return (df, updated_at)."""
        hours = int(hours)
        q = f"SELECT * FROM [call_bell].[fn_report_app_data]({hours})"
        df = st.session_state.sql_user_client.run_query(q)
        updated_at = datetime.now()
        return df, updated_at

    # -----------------------------------------------------------
    # PAGE HEADER
    # -----------------------------------------------------------
    st.title("Call Bell – 24‑hour Summary")
    st.caption("Times are displayed as Hours:Minutes:Seconds")

    df, updated_val = load_data(24)
    if df is None or df.empty:
        st.info("No data found for the last 24 hours.")
        st.stop()

    st.caption(f"Refreshed: {updated_val:%d/%m/%y %H:%M:%S}")

    # Determine home name for the open calls header
    homes = df.get("HomeName", pd.Series(dtype=str)).dropna().unique()
    home_name = homes[0] if len(homes) else "Home"

    # -----------------------------------------------------------
    # HELPERS (events, time)
    # -----------------------------------------------------------
    def format_seconds(seconds) -> str:
        if pd.isna(seconds):
            return ""
        seconds = int(seconds)
        h, rem = divmod(seconds, 3600)
        m, s = divmod(rem, 60)
        return f"{h}:{m:02d}:{s:02d}" if h > 0 else f"{m:02d}:{s:02d}"

    def is_time_column(col: str) -> bool:
        c = (col or "").strip().lower()
        return c in {"waiting time", "care time", "total time", "emergency time"}

    # -----------------------------------------------------------
    # OPEN CALLS
    # -----------------------------------------------------------
    st.subheader(f"{home_name} – Active Open Calls (Not Reset)")
    open_df = (
        df[df["Call Type"].astype(str).str.contains("OPEN", case=False, na=False)]
        .sort_values("Start Time")
        .copy()
        if "Call Type" in df.columns else pd.DataFrame()
    )

    if not open_df.empty:
        open_df = open_df.drop(columns=["HomeName", "Emergency Time"], errors="ignore")
        # Format time columns nicely for display
        for col in open_df.columns:
            if is_time_column(col):
                open_df[col] = open_df[col].map(format_seconds)
        if "Start Date" in open_df.columns:
            open_df["Start Date"] = pd.to_datetime(open_df["Start Date"], errors="coerce")\
                .dt.strftime("%d/%m/%Y %H:%M:%S")
        st.dataframe(open_df, width="stretch", hide_index=True)
    else:
        st.write("No OPEN calls.")

    # -----------------------------------------------------------
    # ROOM SUMMARY
    # -----------------------------------------------------------
    st.divider()
    st.subheader("Room Summary (last 24 hours)")

    WAIT_COL = "Waiting Time"
    CARE_COL = "Care Time"
    TOTAL_COL = "Total Time"
    EMER_COL = "Emergency Time"

    # Create handy seconds fields
    for src, dst in [(WAIT_COL, "WaitingSeconds"),
                     (CARE_COL, "CareSeconds"),
                     (TOTAL_COL, "TotalSeconds"),
                     (EMER_COL, "EmergencySeconds")]:
        if src in df.columns:
            df[dst] = df[src]
        else:
            df[dst] = 0

    # Normalise grouping keys
    for key in ["HomeName", "Room Location"]:
        if key not in df.columns:
            df[key] = "Unknown"
        else:
            df[key] = df[key].fillna("Unknown")

    # Aggregates
    group_keys = ["HomeName", "Room Location"]

    def pct95(s: pd.Series) -> int:
        return int(s.quantile(0.95)) if len(s) else 0

    agg_df = (
        df.groupby(group_keys, dropna=False)
        .agg(
            EventCount=("WaitingSeconds", "size"),
            TotalWaiting=("WaitingSeconds", "sum"),
            AvgWaiting=("WaitingSeconds", "mean"),
            P95Waiting=("WaitingSeconds", pct95),
            TotalCare=("CareSeconds", "sum"),
            TotalEmergency=("EmergencySeconds", "sum"),
            LastEvent=("Start Time", "max") if "Start Time" in df.columns else ("WaitingSeconds", "size")
        )
        .reset_index()
    )

    # Call-type counts per room
    if "Call Type" in df.columns:
        call_type_counts = (
            df.groupby(group_keys + ["Call Type"], dropna=False)
            .size()
            .rename("Count")
            .reset_index()
        )
        call_type_dict = {}
        for _, r in call_type_counts.iterrows():
            key = (r["HomeName"], r["Room Location"])
            call_type_dict.setdefault(key, {})
            label = str(r["Call Type"]) if pd.notna(r["Call Type"]) else "Unknown"
            call_type_dict[key][label] = int(r["Count"])
    else:
        call_type_dict = {}

    # Sort rooms by most active within each home
    homes_order = (
        agg_df.groupby("HomeName", dropna=False)["EventCount"].sum()
        .sort_values(ascending=False)
        .index.tolist()
    )

    # Render summary blocks
    for home in homes_order:
        home_block = agg_df[agg_df["HomeName"] == home].copy()
        home_block = home_block.sort_values(["EventCount", "TotalWaiting"], ascending=[False, False])

        for _, row in home_block.iterrows():
            room = row["Room Location"]
            events = int(row["EventCount"])
            key = (home, room)
            with st.container(border=True):
                st.markdown(f"**{home} - {room}** · {events} events")
                c1, c2, c3, c4, c5 = st.columns(5)
                c1.metric("Total Waiting Time", format_seconds(row["TotalWaiting"]))
                c2.metric("Average Waiting Time", format_seconds(row["AvgWaiting"]))
                c3.metric("95% Waiting Time", format_seconds(row["P95Waiting"]))
                c4.metric("Total Care Time", format_seconds(row["TotalCare"]))
                c5.metric("Total Emergency Time", format_seconds(row["TotalEmergency"]))

                types_counts = call_type_dict.get(key, {})
                if types_counts:
                    pairs = sorted(types_counts.items(), key=lambda x: (-x[1], str(x[0])))
                    stride = 6
                    for i in range(0, len(pairs), stride):
                        row_slice = pairs[i:i+stride]
                        cols = st.columns(len(row_slice))
                        for col, (label, count) in zip(cols, row_slice):
                            col.metric(label, f"{count}")

except Exception as exc:
    fatal_page(exc)