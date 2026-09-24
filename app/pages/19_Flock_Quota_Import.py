"""Routine XLSX import for Flock and Quota Registration records."""

from __future__ import annotations

import uuid

import streamlit as st

from app.auth import can_current, require_page_permission
from app.security import Permission
from app.services.export import spreadsheet_safe
from app.ui import apply_theme, page_header, section_intro
from data.flock_quota_import import (
    MAX_WORKBOOK_BYTES,
    WORKSHEET_NAME,
    WorkbookImportError,
    parse_flock_quota_workbook,
    validate_flock_quota_batch,
)
from data.repositories import get_repository


require_page_permission(Permission.VIEW_DATA)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
may_import = can_current(Permission.IMPORT_DATA)

page_header(
    "Flock & Quota Import",
    "Validate routine Flock and Quota Registration updates before an explicit DEV import.",
    "OPERATIONS",
)

with st.container(border=True):
    section_intro("Select workbook", f"Use the '{WORKSHEET_NAME}' worksheet from the approved batch template.")
    uploaded = st.file_uploader(
        "Flock and Quota workbook",
        type=["xlsx"],
        help="The workbook is parsed in memory and is not saved to the application package.",
        key="flock_quota_upload",
    )
    st.caption("Maximum file size: 10 MB. Upload and validation never write to the database.")

if uploaded is None:
    st.info("Choose an `.xlsx` workbook to begin validation.")
    st.stop()

file_bytes = uploaded.getvalue()
if len(file_bytes) > MAX_WORKBOOK_BYTES:
    st.error("The workbook exceeds the 10 MB import limit.")
    st.stop()

try:
    parsed = parse_flock_quota_workbook(file_bytes, uploaded.name)
    report = validate_flock_quota_batch(parsed, repo)
except WorkbookImportError as exc:
    st.error(str(exc))
    st.stop()
except Exception:
    st.error("The workbook could not be validated safely. Verify the template and try again.")
    st.stop()

if st.session_state.get("flock_quota_fingerprint") != parsed.file_hash:
    st.session_state["flock_quota_fingerprint"] = parsed.file_hash
    st.session_state.pop("flock_quota_import_result", None)
    st.session_state.pop("flock_quota_submitted_hash", None)

existing_import = repo.find_import_by_hash(parsed.file_hash)
frame = report.to_frame()

metrics = st.columns(6)
metrics[0].metric("Total Rows", len(report.record_rows))
metrics[1].metric("Quota Registrations", sum(row.record_type == "QUOTA_REGISTRATION" for row in report.record_rows))
metrics[2].metric("Flocks", sum(row.record_type == "FLOCK" for row in report.record_rows))
metrics[3].metric("Ready", report.ready_count)
metrics[4].metric("Warnings", report.warning_count)
metrics[5].metric("Rejected", report.rejected_count)

with st.container(border=True):
    section_intro("Batch", "File identity and routing summary.")
    left, middle, right = st.columns(3)
    left.markdown(f"**Filename**  \n{uploaded.name}")
    middle.markdown(f"**Batch ID**  \n{report.batch_id or 'Not resolved'}")
    right.markdown(f"**SHA-256**  \n`{parsed.file_hash}`")

with st.container(border=True):
    section_intro("Validation", "Resolve every blocking issue before confirmation.")
    if report.global_errors:
        st.error("Workbook-level validation failed.")
        for message in report.global_errors:
            st.write(f"- {message}")
    if report.global_warnings:
        for message in report.global_warnings:
            st.warning(message)
    if existing_import:
        st.error(f"This exact workbook was already committed as import {existing_import['IMPORT_ID']}.")
    if not report.global_errors and report.rejected_count == 0:
        st.success("All record rows passed blocking validation.")

    view = st.radio(
        "Preview",
        ("All rows", "Ready", "Warnings", "Rejected", "Quota Registrations", "Flocks"),
        horizontal=True,
        key="flock_quota_preview_filter",
    )
    filtered = frame
    if view == "Ready":
        filtered = frame[frame["VALIDATION_STATUS"] == "Ready"]
    elif view == "Warnings":
        filtered = frame[frame["VALIDATION_STATUS"] == "Warning"]
    elif view == "Rejected":
        filtered = frame[frame["VALIDATION_STATUS"] == "Rejected"]
    elif view == "Quota Registrations":
        filtered = frame[frame["RECORD_TYPE"] == "QUOTA_REGISTRATION"]
    elif view == "Flocks":
        filtered = frame[frame["RECORD_TYPE"] == "FLOCK"]
    st.dataframe(filtered, width="stretch", hide_index=True, height=420)

    rejected = frame[frame["VALIDATION_STATUS"] == "Rejected"]
    if not rejected.empty:
        safe_rejected = spreadsheet_safe(rejected)
        st.download_button(
            "Download rejection report",
            safe_rejected.to_csv(index=False).encode("utf-8"),
            file_name=f"{report.batch_id or 'flock-quota'}-rejections.csv",
            mime="text/csv",
            icon=":material/download:",
        )

with st.container(border=True):
    section_intro("Confirm import", "Quota Registrations are written before Flocks in one repository transaction.")
    write_count = len(report.quota_records) + len(report.flock_records)
    st.markdown(f"**Records to write**  \n{write_count:,}")
    if not may_import:
        st.info("Your role may upload and preview this workbook but cannot confirm database changes.")
    if report.global_errors or report.rejected_count:
        st.error("Confirmation is disabled while blocking validation errors remain.")
    if existing_import:
        st.error("Confirmation is disabled because this file hash has already been committed.")

    confirmation_key = f"flock_quota_confirm_{parsed.file_hash[:16]}"
    confirmed = st.checkbox(
        "I reviewed this batch and confirm these DEV-only changes.",
        key=confirmation_key,
        disabled=not may_import or not report.can_import or bool(existing_import),
    )
    already_submitted = st.session_state.get("flock_quota_submitted_hash") == parsed.file_hash
    if st.button(
        "Confirm Import",
        type="primary",
        icon=":material/publish:",
        disabled=(
            not may_import
            or not report.can_import
            or not confirmed
            or bool(existing_import)
            or already_submitted
        ),
    ):
        st.session_state["flock_quota_submitted_hash"] = parsed.file_hash
        try:
            with st.spinner("Importing validated records..."):
                result = repo.import_flock_quota_batch(
                    {
                        "BATCH_ID": report.batch_id,
                        "FILENAME": uploaded.name,
                        "FILE_HASH": parsed.file_hash,
                        "FILE_SIZE_BYTES": parsed.file_size,
                        "ERROR_COUNT": report.rejected_count,
                        "NOTES": f"Routine Flock & Quota Import batch {report.batch_id}.",
                    },
                    report.quota_records,
                    report.flock_records,
                )
            st.session_state["flock_quota_import_result"] = result
            st.success(
                f"Committed {result['total_count']} records: "
                f"{result['created_count']} created and {result['updated_count']} updated."
            )
            if result.get("audit_recorded") is False:
                st.warning("Core records were committed, but the separate audit event could not be recorded.")
        except Exception:
            st.session_state.pop("flock_quota_submitted_hash", None)
            reference = uuid.uuid4().hex[:12].upper()
            st.error(f"The import was rolled back. Error reference: {reference}")

result = st.session_state.get("flock_quota_import_result")
if result and result.get("file_hash") == parsed.file_hash:
    with st.container(border=True):
        section_intro("Import result", "The committed batch is protected from duplicate submission by file hash.")
        cols = st.columns(4)
        cols[0].metric("Status", result["status"])
        cols[1].metric("Created", result["created_count"])
        cols[2].metric("Updated", result["updated_count"])
        cols[3].metric("Total", result["total_count"])
        st.caption(f"Import ID: {result['import_id']}")
        if result.get("audit_recorded") is False:
            st.warning("The separate audit event was not recorded. Ask an administrator to review the audit service.")
