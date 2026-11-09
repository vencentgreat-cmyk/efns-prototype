"""In-memory, schema-agnostic profiling for source CSV and Excel files."""

from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.auth import require_page_permission
from app.security import Permission
from app.services.profiling_export import profile_csv, profiles_excel
from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.profiling import (
    ProfilingError,
    candidate_primary_keys,
    candidate_relationship_columns,
    profile_dataframe,
    read_tabular,
)


require_page_permission(Permission.USE_PROFILER)
apply_theme()
page_header(
    "Source Data Profiler",
    "Inspect arbitrary tabular source files before authoritative source-to-target mapping begins.",
    "ADMINISTRATION",
)

st.info(
    "Files are analyzed locally in memory for this session. They are not saved, sent to Snowflake, "
    "or matched to EFNS entities. Type and relationship results are heuristic suggestions."
)

uploaded = st.file_uploader(
    "Upload source data",
    type=["csv", "xlsx", "xlsm"],
    help="Uses the Streamlit server's configured upload-size limit. Large workbooks require memory for all worksheets.",
)

if uploaded is None:
    with st.container(border=True):
        section_intro("No source selected", "Upload a CSV, XLSX, or XLSM file to create an in-memory profile.")
    st.stop()

size = int(getattr(uploaded, "size", 0) or 0)
st.caption(f"Source: {uploaded.name} · {size / 1024:,.1f} KB")

try:
    frames = read_tabular(uploaded, uploaded.name)
    profiles = {name: profile_dataframe(frame) for name, frame in frames.items()}
    key_suggestions = {name: candidate_primary_keys(frame) for name, frame in frames.items()}
    relationship_suggestions = {
        name: candidate_relationship_columns(frame) for name, frame in frames.items()
    }
except ProfilingError as exc:
    show_data_error(exc)
    st.stop()
except Exception:
    st.error("The source could not be profiled. Confirm that the file is readable and try again.")
    st.stop()

sheet_names = list(frames)
selected_sheet = (
    st.selectbox("Worksheet", sheet_names, key="source_profiler_sheet")
    if len(sheet_names) > 1
    else sheet_names[0]
)
if len(sheet_names) == 1:
    st.caption(f"Data section: {selected_sheet}")

profile = profiles[selected_sheet]
section_intro("Profile summary", f"Advisory statistics for {selected_sheet}.")
metrics = st.columns(3)
metrics[0].metric("Rows", f"{profile.row_count:,}")
metrics[1].metric("Columns", f"{profile.column_count:,}")
metrics[2].metric("Duplicate rows", f"{profile.duplicate_row_count:,}")

suggestions = st.columns(2)
with suggestions[0].container(border=True):
    section_intro("Candidate primary keys", "Unique, non-null single columns; confirmation requires source metadata.")
    keys = key_suggestions[selected_sheet]
    st.write(", ".join(keys) if keys else "No candidates found.")
with suggestions[1].container(border=True):
    section_intro("Relationship-like columns", "Name/cardinality suggestions only; these are not confirmed relationships.")
    relationships = relationship_suggestions[selected_sheet]
    st.write(", ".join(relationships) if relationships else "No suggestions found.")

section_intro("Column profile", "Inferred types are conservative and do not change the uploaded values.")
st.dataframe(
    profile.column_profile,
    width="stretch",
    hide_index=True,
    column_config={
        "COLUMN_NAME": st.column_config.TextColumn("Source Column"),
        "INFERRED_TYPE": st.column_config.TextColumn("Suggested Type"),
        "NULL_RATIO": st.column_config.NumberColumn("Null Ratio", format="percent"),
        "UNIQUE_RATIO": st.column_config.NumberColumn("Unique Ratio", format="percent"),
        "DATE_MIN": st.column_config.DateColumn("Date Minimum", format="YYYY-MM-DD"),
        "DATE_MAX": st.column_config.DatetimeColumn("Date/Time Maximum", format="YYYY-MM-DD HH:mm"),
    },
)

section_intro("Profiling report", "Downloads contain summary/profile results and limited samples, not the full source dataset.")
stem = Path(uploaded.name).stem or "source"
downloads = st.columns(2)
downloads[0].download_button(
    "Download selected profile (CSV)",
    data=profile_csv(profile),
    file_name=f"{stem}_{selected_sheet}_profile.csv",
    mime="text/csv",
    icon=":material/download:",
    width="stretch",
)
downloads[1].download_button(
    "Download workbook profile (Excel)",
    data=profiles_excel(profiles, key_suggestions, relationship_suggestions),
    file_name=f"{stem}_profiling_report.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    icon=":material/download:",
    width="stretch",
)
