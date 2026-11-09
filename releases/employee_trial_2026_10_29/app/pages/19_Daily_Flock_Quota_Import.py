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
from data.repositories.base import RepositoryError


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
                if may_import:
                    archives = {}
                    for upload in uploads:
                        archived = repo.archive_source_file(upload.name, upload.getvalue(), "DAILY_FLOCK_QUOTA")
                        archives[upload.name + "\0" + archived["FILE_HASH"]] = archived["SOURCE_FILE_ID"]
                    st.session_state.daily_source_files = archives
                report = analyze_operational_files(
                    uploads, selected_type, repo, max_file_bytes=max_upload_mb * 1024 * 1024
                )
                if may_import:
                    for item in report.files:
                        file_id = archives[item.filename + "\0" + item.file_hash]
                        repo.record_source_parse(file_id,not any("could not be parsed" in error for error in item.errors))
                    source_rows=[{**row,"SOURCE_FILE_ID":archives[row["RAW_DATA"]["source_filename"]+"\0"+(row["RAW_DATA"].get("source_file_hash") or "")]} for row in report.raw_rows]
                    st.session_state.daily_prepared_import_id=repo.stage_operational_review({
                        "FILENAME":report.files[0].filename if len(report.files)==1 else f"Operational upload ({len(report.files)} files)",
                        "FILE_HASH":report.package_hash,"FILE_SIZE_BYTES":sum(item.file_size for item in report.files),
                    },source_rows)
                    st.session_state.daily_prepared_package_hash=report.package_hash
            st.session_state.daily_flock_quota_report = report
            st.session_state.pop("daily_flock_quota_result", None)
            st.session_state.pop("daily_flock_quota_submitted_hash", None)
        except OperationalImportError as exc:
            st.error(str(exc))
        except Exception as exc:
            show_data_error(exc)

report = st.session_state.get("daily_flock_quota_report")
if report is None:
    st.info("Choose one or more files, then select Review and validate. Original files are archived for import users; no business records are written during review.")
    st.stop()

existing_import = repo.find_import_by_hash(report.package_hash)
already_committed = bool(existing_import and str(existing_import.get("STATUS","")).lower()=="committed")
prepared_for_commit=st.session_state.get("daily_prepared_package_hash")==report.package_hash
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
    if already_committed:
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
        disabled=not may_import or not prepared_for_commit or not report.ready_rows or already_committed,
    )
    unknown_reference = st.session_state.get("daily_flock_quota_unknown_outcomes", {}).get(report.package_hash)
    if unknown_reference:
        st.error(f"The save outcome is unknown. Do not submit this file again. Ask an administrator to check the import history (reference: {unknown_reference}).")
    already_submitted = bool(unknown_reference) or st.session_state.get("daily_flock_quota_submitted_hash") == report.package_hash
    if st.button(
        "Confirm import",
        type="primary",
        icon=":material/publish:",
        disabled=not may_import or not prepared_for_commit or not report.ready_rows or not confirmed or already_committed or already_submitted,
    ):
        st.session_state.daily_flock_quota_submitted_hash = report.package_hash
        try:
            with st.spinner("Saving the validated rows..."):
                result = repo.commit_staged_operational(
                    st.session_state.daily_prepared_import_id,
                    report.records_by_entity,
                )
            st.session_state.daily_flock_quota_result = result
            st.success(
                f"Imported {result['total_count']:,} rows: "
                f"{result['created_count']:,} created and {result['updated_count']:,} updated."
            )
        except Exception as exc:
            # The executor uses this explicit RepositoryError marker after a
            # COMMIT acknowledgement fails; it is not proof of rollback.
            if isinstance(exc, RepositoryError) and str(exc).startswith('COMMIT outcome is unknown.'):
                reference = st.session_state.get('daily_prepared_import_id') or uuid.uuid4().hex[:12].upper()
                pending = dict(st.session_state.get('daily_flock_quota_unknown_outcomes', {}))
                pending[report.package_hash] = reference
                st.session_state.daily_flock_quota_unknown_outcomes = pending
                st.error(f"The save outcome is unknown. Do not submit this file again. Ask an administrator to check the import history (reference: {reference}).")
            elif isinstance(exc, RepositoryError) and str(exc).startswith('System busy: no write transaction started'):
                # Explicit executor evidence that BEGIN was never entered.
                st.session_state.pop("daily_flock_quota_submitted_hash", None)
                reference = uuid.uuid4().hex[:12].upper()
                st.error(f"No business rows were committed. Original files and staged source rows remain available. Error reference: {reference}")
            else:
                # No typed rollback receipt exists at this boundary. Preserve
                # the submission guard and show the ordinary safe error.
                show_data_error(exc)

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
