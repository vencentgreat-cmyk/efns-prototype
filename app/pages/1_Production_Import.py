"""Upload, validate, preview, and import an EIMS production workbook."""

from __future__ import annotations

import hashlib
import io

import streamlit as st

from app.ui import apply_theme, page_header, section_intro
from data.constants import EIMS_WORKSHEET_NAME
from data.importing import (
    build_raw_rows,
    normalize_eims_records,
    read_eims_workbook,
    validate_eims_records,
)
from data.repositories import get_repository


apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

page_header(
    "Production Import",
    "Load the saved EIMS 3 worksheet, review technical validation, and preserve both raw and normalized records.",
    "PRODUCTION",
)

with st.container(border=True):
    section_intro("Workbook requirements", "Use the standard saved EIMS production workbook.")
    col_a, col_b, col_c = st.columns(3)
    col_a.markdown("**File type**  \nExcel `.xlsx` or `.xlsm`")
    col_b.markdown(f"**Worksheet**  \n`{EIMS_WORKSHEET_NAME}`")
    col_c.markdown("**Source area**  \nColumns A through AI")
    st.info(
        "The importer reads values already saved in Excel. It does not execute macros or recalculate formulas."
    )

with st.container(border=True):
    section_intro("Select workbook", "The file remains in the current in-memory session.")
    uploaded = st.file_uploader(
        "EIMS production workbook",
        type=["xlsm", "xlsx"],
        help="Choose a workbook containing the EIMS 3 worksheet.",
        label_visibility="collapsed",
    )

if uploaded is None:
    st.info("Choose an EIMS production workbook to begin validation.")
    st.stop()

file_bytes = uploaded.getvalue()
file_hash = hashlib.sha256(file_bytes).hexdigest()
existing_import = repo.find_import_by_hash(file_hash)
try:
    raw_df = read_eims_workbook(io.BytesIO(file_bytes))
except ValueError:
    st.error(f"The workbook does not contain a readable '{EIMS_WORKSHEET_NAME}' worksheet.")
    st.stop()
except Exception as exc:
    st.error(f"Unable to read the workbook: {exc}")
    st.stop()

errors, warnings = validate_eims_records(raw_df)
normalized_df = normalize_eims_records(raw_df)

metric_columns = st.columns(4)
metric_columns[0].metric("Production Records", len(raw_df))
metric_columns[1].metric("Columns Detected", len(raw_df.columns) - 1)
metric_columns[2].metric("Blocking Errors", len(errors))
metric_columns[3].metric("Warnings", len(warnings))

with st.container(border=True):
    section_intro(
        "Source and matching status",
        "The workbook source is preserved. Account, facility, and flock relationships remain unmatched until reviewed.",
    )
    source_col, match_col = st.columns(2)
    source_col.markdown(f"**Worksheet source**  \n`{EIMS_WORKSHEET_NAME}` · columns A through AI")
    match_counts = normalized_df.get("MATCH_STATUS")
    if match_counts is None:
        match_col.markdown("**Relationship status**  \nNot available")
    else:
        statuses = match_counts.fillna("Unmatched").astype(str).value_counts().to_dict()
        status_text = ", ".join(f"{name}: {count}" for name, count in statuses.items())
        match_col.markdown(f"**Relationship status**  \n{status_text}")

with st.container(border=True):
    section_intro("Technical validation", "Required columns, reporting period, and numeric checks.")
    allow_duplicate = False
    if existing_import:
        st.warning(f"This exact file was already imported as {existing_import['IMPORT_ID']}.")
        allow_duplicate = st.checkbox("Import this duplicate file anyway")
    if errors:
        st.error(f"{len(errors)} blocking validation error(s) found.")
        for error in errors[:30]:
            st.write(f"• {error}")
    else:
        st.success("No blocking validation errors were found.")
    if warnings:
        st.warning(f"{len(warnings)} non-blocking warning(s) found.")
        for warning in warnings[:30]:
            st.write(f"• {warning}")

with st.expander("Source-preserving preview · first 50 rows", expanded=False):
    with st.container(border=True):
        st.dataframe(raw_df.head(50), width="stretch", height=380, hide_index=True)

with st.expander("Normalized preview · first 50 rows", expanded=False):
    with st.container(border=True):
        section_intro(
            "Normalized import model",
            "Relationships remain unmatched until authoritative Dataverse metadata is available.",
        )
        priority_columns = [
            "SOURCE_ROW_NUMBER",
            "SOURCE_WEEK_CODE",
            "REPORTING_YEAR",
            "REPORTING_WEEK",
            "PRODUCER_NUMBER",
            "GRADER_NUMBER",
            "MARKETING_TYPE",
            "HOUSING_SYSTEM",
            "EGG_TYPE",
            "EGG_COLOUR",
            "TOTAL",
            "SOURCE_TYPE",
            "MATCH_STATUS",
        ]
        columns = [column for column in priority_columns if column in normalized_df.columns]
        st.dataframe(
            normalized_df[columns].head(50),
            width="stretch",
            height=380,
            hide_index=True,
        )

with st.container(border=True):
    section_intro("Import to current repository", "Raw rows and normalized records are stored together for traceability.")
    filename = st.text_input("Source filename", value=uploaded.name)
    years = normalized_df["REPORTING_YEAR"].dropna().astype(int).unique()
    weeks = normalized_df["REPORTING_WEEK"].dropna().astype(int).unique()
    batch_year = int(years[0]) if len(years) == 1 else None
    batch_week = int(weeks[0]) if len(weeks) == 1 else None

    if errors:
        st.error("Import is disabled until all blocking errors are resolved.")

    confirm_import = st.checkbox(
        "I reviewed the validation results and want to import these records.",
        disabled=bool(errors),
    )
    if st.button(
        "Import validated records",
        type="primary",
        disabled=bool(errors) or not confirm_import or bool(existing_import and not allow_duplicate),
    ):
        try:
            import_id, imported_count = repo.import_production_bundle(
                {
                    "FILENAME": filename,
                    "SOURCE": "EIMS Production Workbook - EIMS 3",
                    "REPORTING_YEAR": batch_year,
                    "REPORTING_WEEK": batch_week,
                    "STATUS": "Validated",
                    "ERROR_COUNT": len(errors),
                    "NOTES": "Imported from the EIMS 3 worksheet.",
                    "FILE_HASH": file_hash,
                    "FILE_SIZE_BYTES": len(file_bytes),
                    "WORKSHEET_NAME": EIMS_WORKSHEET_NAME,
                    "SOURCE_RECORD_COUNT": len(raw_df),
                },
                build_raw_rows(raw_df, "VALID", warnings),
                normalized_df,
                allow_duplicate=allow_duplicate,
            )
            st.success(f"Imported {imported_count} production records.")
            st.code(import_id, language=None)
        except Exception as exc:
            st.error(f"Import failed: {exc}")
