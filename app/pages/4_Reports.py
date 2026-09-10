# ============================================================
# EFNS Prototype v0.1 — Reports Page
# ============================================================
"""Customizable report builder with field selection, preview, and export."""

import io

import pandas as pd
import streamlit as st

from data.repositories import get_repository
from services.report_builder import REPORT_FIELDS, build_report


st.set_page_config(page_title="Reports", page_icon="🥚")

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

st.title("Customizable Reports")
st.caption("Select fields from multiple operational areas to build a dynamic report.")

st.warning(
    "Joins between production and account/facility/flock are **PROVISIONAL** "
    "(linked via FLOCK_ID). This will be revised after Dataverse metadata is obtained."
)

# --- Field Selection ---
st.markdown("### Select Report Fields")

selected_keys = []

for section, fields in REPORT_FIELDS.items():
    with st.expander(f"{section} Fields", expanded=section in ("Account", "Production")):
        for key, display_name, _col in fields:
            if st.checkbox(display_name, value=False, key=f"rpt_{key}"):
                selected_keys.append(key)

if not selected_keys:
    st.info("Select fields above to build a report.")
    st.stop()

# --- Build Report ---
st.divider()
st.subheader("Report Preview")

with st.spinner("Building report..."):
    try:
        report_df = build_report(repo, selected_keys)
    except Exception as e:
        st.error(f"Error building report: {e}")
        st.stop()

st.write(f"**Rows:** {len(report_df)}  |  **Columns:** {len(report_df.columns)}")
st.dataframe(report_df.head(100), use_container_width=True, hide_index=True)

# --- Export ---
st.divider()
st.subheader("Export")

col1, col2 = st.columns(2)

with col1:
    csv_buffer = io.StringIO()
    report_df.to_csv(csv_buffer, index=False)
    st.download_button(
        "📥 Export CSV",
        csv_buffer.getvalue(),
        "efns_report.csv",
        "text/csv",
        use_container_width=True,
    )

with col2:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        report_df.to_excel(writer, index=False, sheet_name="EFNS Report")
    excel_buffer.seek(0)
    st.download_button(
        "📥 Export Excel",
        excel_buffer.getvalue(),
        "efns_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

st.caption("Both CSV and Excel export are supported.")