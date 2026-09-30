"""Daily and incremental Flock and Quota file import."""

from __future__ import annotations

import uuid

import pandas as pd
import streamlit as st

from app.auth import can_current, require_page_permission
from app.security import Permission
from app.services.export import spreadsheet_safe
from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.operational_flock_quota_import import (
    ENTITY_DISPLAY,
    ENTITY_LABELS,
    OperationalImportError,
    analyze_operational_files,
)
from data.repositories import get_repository


require_page_permission(Permission.VIEW_DATA)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
may_import = can_current(Permission.IMPORT_DATA)
max_upload_mb = int(st.get_option("server.maxUploadSize"))

page_header(
    "Daily Flock & Quota Import",
    "Upload one file or several ordinary updates, review every row, then confirm the import.",
    "OPERATIONS",
)

with st.container(border=True):
    section_intro("Upload files", "A single file is enough. Files do not need fixed names or companion files.")
    selected_type = st.selectbox("What does the upload contain?", tuple(ENTITY_LABELS))
    uploads = st.file_uploader(
        "Choose CSV or Excel files",
        type=["csv", "xlsx", "xlsm"],
        accept_multiple_files=True,
        help=f"Each file may be up to {max_upload_mb} MB.",
        key="daily_flock_quota_uploads",
    )
    st.caption(f"Accepted formats: CSV, XLSX and XLSM. Maximum size per file: {max_upload_mb} MB.")
    if st.button(
        "Review and validate",
        type="primary",
        icon=":material/fact_check:",
        disabled=not uploads,
    ):
        try:
            with st.spinner("Checking the uploaded rows..."):
                report = analyze_operational_files(
                    uploads, selected_type, repo, max_file_bytes=max_upload_mb * 1024 * 1024
                )
            st.session_state.daily_flock_quota_report = report
            st.session_state.pop("daily_flock_quota_result", None)
            st.session_state.pop("daily_flock_quota_submitted_hash", None)
        except OperationalImportError as exc:
            st.error(str(exc))
        except Exception as exc:
            show_data_error(exc)

report = st.session_state.get("daily_flock_quota_report")
if report is None:
    st.info("Choose one or more files, then select Review and validate. Nothing is saved during review.")
    st.stop()

existing_import = repo.find_import_by_hash(report.package_hash)
row_frame = report.rows_frame()

metrics = st.columns(5)
metrics[0].metric("Files", len(report.files))
metrics[1].metric("Unsupported files", len(report.unsupported_files))
metrics[2].metric("Source rows", sum(item.row_count for item in report.files))
metrics[3].metric("Valid rows", len(report.ready_rows))
metrics[4].metric("Rejected rows", len(report.rejected_rows))

with st.container(border=True):
    section_intro("File review", "Detected contents and a short preview from each file.")
    summary = pd.DataFrame([
        {
            "File name": item.filename,
            "Detected contents": (
                f"Unsupported: {item.errors[0].removeprefix('Unsupported entity: ').rstrip('.')}"
                if item.unsupported_entity else ENTITY_DISPLAY.get(item.entity, "Could not detect")
            ),
            "Rows": item.row_count,
            "File status": "Unsupported" if item.unsupported_entity else ("Needs attention" if item.errors else "Ready for row checks"),
        }
        for item in report.files
    ])
    st.dataframe(summary, hide_index=True, width="stretch")
    for item in report.files:
        with st.expander(f"Preview: {item.filename}"):
            if item.errors:
                for message in item.errors:
                    st.error(message)
            if not item.preview.empty:
                st.dataframe(item.preview, hide_index=True, width="stretch", height=260)

with st.container(border=True):
    section_intro("Validation results", "Unsupported files and rejected rows are never imported.")
    if existing_import:
        st.error("This exact set of files has already been imported.")
    elif report.unsupported_files and not report.ready_rows:
        st.warning("The uploaded files contain data that this page does not support.")
    elif report.rejected_rows or report.unsupported_files:
        st.warning("Some rows need correction. Valid rows may still be imported after review.")
    elif report.ready_rows:
        st.success("All rows passed validation.")
    else:
        st.error("There are no valid rows to import.")

    status_filter = st.segmented_control(
        "Rows to show",
        ("All rows", "Valid", "Rejected", "Unsupported"),
        default="All rows",
        key="daily_flock_quota_status_filter",
    )
    shown = row_frame
    if status_filter == "Valid":
        shown = row_frame[row_frame["STATUS"] == "Ready"]
    elif status_filter == "Rejected":
        shown = row_frame[row_frame["STATUS"] == "Rejected"]
    elif status_filter == "Unsupported":
        shown = row_frame[row_frame["STATUS"] == "Unsupported"]
    st.dataframe(shown.head(500), hide_index=True, width="stretch", height=420)
    if len(shown) > 500:
        st.caption("The on-screen preview is limited to 500 rows. Counts include the full upload.")

    issues = row_frame[row_frame["STATUS"].isin(["Rejected", "Unsupported"])]
    if not issues.empty:
        safe_issues = spreadsheet_safe(issues)
        st.download_button(
            "Download issue report",
            safe_issues.to_csv(index=False).encode("utf-8-sig"),
            file_name="daily-flock-quota-errors.csv",
            mime="text/csv",
            icon=":material/download:",
        )

with st.container(border=True):
    section_intro("Confirm import", "Only valid rows will be saved. They are committed together or not at all.")
    entity_counts = {
        ENTITY_DISPLAY[entity]: len(records)
        for entity, records in report.records_by_entity.items()
        if records
    }
    if entity_counts:
        st.dataframe(
            pd.DataFrame([{"Contents": name, "Rows to import": count} for name, count in entity_counts.items()]),
            hide_index=True,
            width="stretch",
        )
    if not may_import:
        st.info("Your role can review files but cannot confirm an import.")
    confirmed = st.checkbox(
        "I reviewed the validation results and confirm the valid rows for import.",
        key=f"daily_flock_quota_confirm_{report.package_hash[:16]}",
        disabled=not may_import or not report.ready_rows or bool(existing_import),
    )
    already_submitted = st.session_state.get("daily_flock_quota_submitted_hash") == report.package_hash
    if st.button(
        "Confirm import",
        type="primary",
        icon=":material/publish:",
        disabled=not may_import or not report.ready_rows or not confirmed or bool(existing_import) or already_submitted,
    ):
        st.session_state.daily_flock_quota_submitted_hash = report.package_hash
        try:
            with st.spinner("Saving the validated rows..."):
                result = repo.import_operational_flock_quota_batch(
                    {
                        "FILENAME": ", ".join(item.filename for item in report.files),
                        "FILE_HASH": report.package_hash,
                        "FILE_SIZE_BYTES": sum(item.file_size for item in report.files),
                        "NOTES": "Daily or incremental Flock and Quota operational import.",
                    },
                    report.records_by_entity,
                    report.raw_rows,
                )
            st.session_state.daily_flock_quota_result = result
            st.success(
                f"Imported {result['total_count']:,} rows: "
                f"{result['created_count']:,} created and {result['updated_count']:,} updated."
            )
        except Exception:
            st.session_state.pop("daily_flock_quota_submitted_hash", None)
            reference = uuid.uuid4().hex[:12].upper()
            st.error(f"Nothing was saved. Error reference: {reference}")

result = st.session_state.get("daily_flock_quota_result")
if result and result.get("file_hash") == report.package_hash:
    with st.container(border=True):
        section_intro("Import complete", "This upload is now protected from accidental repeat submission.")
        result_metrics = st.columns(4)
        result_metrics[0].metric("Status", result["status"])
        result_metrics[1].metric("Created", result["created_count"])
        result_metrics[2].metric("Updated", result["updated_count"])
        result_metrics[3].metric("Imported", result["total_count"])
        st.caption(f"Import reference: {result['import_id']}")
