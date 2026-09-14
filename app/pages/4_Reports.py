# ============================================================
# EFNS Prototype v0.1 — Reports Page
# ============================================================
"""Customizable report builder with field selection, preview, and export."""

import io

import pandas as pd
import streamlit as st

from app.auth import require_page_permission
from app.security import Permission
from app.services.export import spreadsheet_safe
from app.ui import apply_theme, page_header, section_intro
from data.repositories import get_repository
from app.services.report_builder import REPORT_FIELDS, build_report

require_page_permission(Permission.VIEW_REPORTS)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

page_header(
    "Custom Reports",
    "Choose operational fields, preview the joined result, and export a controlled dataset.",
    "REPORTING",
)
st.info("Production relationships use the provisional FLOCK_ID link pending Dataverse metadata.")

# --- Field Selection ---
section_intro("Select report fields", "Expand each business area and choose the fields to include.")

selected_keys = []
field_groups = list(REPORT_FIELDS.items())
field_tabs = st.tabs([f"{section} ({len(fields)})" for section, fields in field_groups])

for field_tab, (_section, fields) in zip(field_tabs, field_groups):
    with field_tab:
        field_columns = st.columns(2)
        for index, (key, display_name, _col) in enumerate(fields):
            with field_columns[index % 2]:
                if st.checkbox(display_name, value=False, key=f"rpt_{key}"):
                    selected_keys.append(key)

st.caption(f"Selected fields: {len(selected_keys)}")

if not selected_keys:
    st.info("No fields selected. Choose one or more fields above to create the preview and export files.")
    st.stop()

# --- Build Report ---
section_intro("Report preview", "The preview shows the first 100 rows.")

with st.spinner("Building report..."):
    try:
        report_df = build_report(repo, selected_keys)
    except Exception as e:
        st.error(f"Error building report: {e}")
        st.stop()

st.write(f"**Rows:** {len(report_df)}  |  **Columns:** {len(report_df.columns)}")
st.dataframe(report_df.head(100), width="stretch", height=470, hide_index=True)

# --- Export ---
section_intro("Export", "Spreadsheet-safe CSV and Excel files use the current report result.")

col1, col2 = st.columns(2)

with col1:
    csv_buffer = io.StringIO()
    export_df = spreadsheet_safe(report_df)
    export_df.to_csv(csv_buffer, index=False)
    st.download_button(
        "Export report as CSV",
        csv_buffer.getvalue(),
        "efns_report.csv",
        "text/csv",
        width="stretch",
    )

with col2:
    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        export_df.to_excel(writer, index=False, sheet_name="EFNS Report")
    excel_buffer.seek(0)
    st.download_button(
        "Export report as Excel",
        excel_buffer.getvalue(),
        "efns_report.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        width="stretch",
    )

st.caption("Both CSV and Excel export are supported.")
