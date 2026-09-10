# ============================================================
# EFNS Internal Data System Prototype v0.1
# Main Streamlit App
# ============================================================
"""Entry point: `streamlit run app/app.py`"""

import streamlit as st

# MUST be the first Streamlit command
st.set_page_config(
    page_title="EFNS Internal Data System",
    page_icon="🥚",
    layout="wide",
    initial_sidebar_state="expanded",
)

from data.repositories import get_repository


def init_session_state():
    """Set up session-level singletons if not already present."""
    if "repo" not in st.session_state:
        st.session_state.repo = get_repository()


# ------------------------------------------------------------------
# Page registry (no framework — plain Streamlit multipage via pages/ dir)
# The pages/ directory is auto-detected by Streamlit.
# This file serves as the Home page.
# ------------------------------------------------------------------

init_session_state()

repo = st.session_state.repo
metrics = repo.get_production_summary_metrics()

# ------------------------------------------------------------------
# Sidebar
# ------------------------------------------------------------------
with st.sidebar:
    st.title("🥚 EFNS Prototype v0.1")
    st.caption("Egg Farmers of Nova Scotia")
    st.divider()
    st.markdown("### Navigation")
    st.markdown("Use the sidebar pages above to navigate.")
    st.divider()
    st.markdown("### Status")
    st.success(f"Repository: {'Mock (local)' if 'Mock' in type(repo).__name__ else 'Snowflake'}")
    st.caption("**PROVISIONAL SCHEMA** — pending Dataverse inspection")

# ------------------------------------------------------------------
# Home page content
# ------------------------------------------------------------------
st.title("EFNS Internal Data System")
st.subheader("Prototype v0.1")
st.caption("Egg Farmers of Nova Scotia — Internal Data System")

st.divider()

# Summary metrics
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Accounts", metrics.get("account_count", 0))
with col2:
    st.metric("Flocks", metrics.get("flock_count", 0))
with col3:
    st.metric("Production Records", metrics.get("production_record_count", 0))
with col4:
    st.metric("Imports", metrics.get("import_count", 0))

st.divider()

col_a, col_b, col_c, col_d = st.columns(4)
with col_a:
    st.metric("Total Received", f"{metrics.get('total_received', 0):,.1f}")
with col_b:
    st.metric("Total Accepted", f"{metrics.get('total_accepted', 0):,.1f}")
with col_c:
    st.metric("Total Rejected", f"{metrics.get('total_rejected', 0):,.1f}")
with col_d:
    st.metric("Total Loss", f"{metrics.get('total_loss', 0):,.1f}")

st.divider()

# Recent imports
st.subheader("Recent Imports")
imports = repo.get_import_batches()
if not imports.empty:
    st.dataframe(
        imports[["IMPORT_ID", "FILENAME", "SOURCE", "REPORTING_YEAR",
                  "REPORTING_WEEK", "ROW_COUNT", "STATUS", "UPLOAD_TIMESTAMP"]]
        .sort_values("UPLOAD_TIMESTAMP", ascending=False)
        .head(10),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No import batches yet. Use the Production Import page to upload a CSV.")

st.divider()

st.markdown("""
### About This Prototype

This is **Prototype v0.1** of the EFNS Internal Data System. It is built with:

- **Python** + **Streamlit** (UI)
- **Snowflake-compatible SQL** (data layer)
- **Modular repository pattern** (currently running in local/mock mode)

**Important:** All schema, relationships, and business rules are **PROVISIONAL**.
They will be revised after the existing EIMS Dataverse environment metadata is
reverse-engineered.

Navigate using the sidebar to explore:

1. **Production Import** — Upload and validate CSV production data
2. **Production Data** — Search, filter, and view production records
3. **Accounts / Facilities / Flocks** — CRUD-style operational views
4. **Reports** — Customizable field selection and export
""")