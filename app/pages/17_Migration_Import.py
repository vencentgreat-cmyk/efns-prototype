"""Historical EIMS migration workspace (provisional metadata contract)."""

from __future__ import annotations

import streamlit as st

from app.auth import require_page_permission
from app.security import Permission, has_permission
from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.migration import analyze_migration_files, expected_filenames, load_mapping
from data.repositories import get_repository


user = require_page_permission(Permission.IMPORT_DATA)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
mapping = load_mapping()

page_header(
    "Historical EIMS Migration",
    "Stage, validate, reconcile, and commit a provisional historical export package.",
    "MIGRATION",
)

st.warning(
    "This workflow uses a provisional mapping pending authoritative EIMS metadata. "
    "Daily Production Import remains a separate workflow."
)

with st.container(border=True):
    section_intro("Expected package", "Upload all files together. Filenames must match exactly.")
    st.code("\n".join(expected_filenames(mapping)), language=None)
    uploads = st.file_uploader(
        "Historical EIMS export files",
        type=["csv", "xlsx", "xlsm"],
        accept_multiple_files=True,
    )
    if st.button("Validate package", type="primary", disabled=not uploads):
        try:
            st.session_state.eims_migration_analysis = analyze_migration_files(uploads, mapping)
        except Exception as exc:
            show_data_error(exc)

analysis = st.session_state.get("eims_migration_analysis")
if analysis is not None:
    duplicate = repo.find_migration_by_hash(analysis.package_hash)
    relationship_errors = analysis.errors["FIELD_MESSAGE"].str.contains(
        "references|belong|own", case=False, regex=True
    ).sum() if not analysis.errors.empty else 0
    metrics = st.columns(6)
    metrics[0].metric("Source rows", len(analysis.raw_rows))
    metrics[1].metric("Ready", analysis.ready_count)
    metrics[2].metric("Rejected", analysis.rejected_count)
    metrics[3].metric("Files", len(analysis.files))
    metrics[4].metric("Warnings", 0)
    metrics[5].metric("Relationship mismatches", int(relationship_errors))

    with st.container(border=True):
        section_intro("Reconciliation", "Counts remain traceable from source files through validation.")
        file_summary = [
            {
                "Filename": row["SOURCE_FILENAME"], "Entity": row["SOURCE_ENTITY"],
                "Rows": row["SOURCE_ROW_COUNT"], "Bytes": row["FILE_SIZE_BYTES"],
                "SHA-256": row["FILE_HASH"],
            }
            for row in analysis.files
        ]
        st.dataframe(file_summary, hide_index=True, width="stretch")
        st.dataframe(analysis.reconciliation, hide_index=True, width="stretch")
        if analysis.errors.empty:
            st.success("All source rows passed the provisional validation contract.")
        else:
            st.error("Rejected rows must be reviewed. Only Ready rows are eligible for commit.")
            st.dataframe(analysis.errors, hide_index=True, width="stretch")
            st.download_button(
                "Download rejected-row report",
                analysis.errors.to_csv(index=False).encode("utf-8"),
                file_name=f"{analysis.batch_id}_rejections.csv",
                mime="text/csv",
            )

    with st.container(border=True):
        section_intro("Prepare RAW batch", "Files are staged first; raw and normalized values are then recorded for traceability.")
        if duplicate:
            st.warning(f"This package is already registered as {duplicate['MIGRATION_BATCH_ID']}.")
        confirmed = st.checkbox("I confirm this package contains only approved synthetic or authorized EIMS migration data.")
        if st.button("Stage and prepare migration", disabled=bool(duplicate) or not confirmed):
            try:
                file_rows = []
                for source in analysis.files:
                    stage_path = repo.stage_migration_file(
                        analysis.batch_id, source["SOURCE_FILENAME"], source["CONTENT"]
                    )
                    file_rows.append({**source, "STAGE_PATH": stage_path})
                status = "READY" if analysis.rejected_count == 0 else "PARTIAL"
                repo.prepare_migration_batch(
                    {
                        "MIGRATION_BATCH_ID": analysis.batch_id,
                        "PACKAGE_HASH": analysis.package_hash,
                        "SCHEMA_VERSION": analysis.schema_version,
                        "STATUS": status,
                        "CREATED_BY": user.email,
                    },
                    file_rows,
                    analysis.raw_rows,
                )
                st.session_state.eims_prepared_batch_id = analysis.batch_id
                st.success("The migration batch is staged and preserved in RAW.")
            except Exception as exc:
                show_data_error(exc)

    prepared = st.session_state.get("eims_prepared_batch_id")
    if prepared == analysis.batch_id:
        with st.container(border=True):
            section_intro("Commit Ready rows", "The CORE write follows dependency order and rolls back as one transaction on failure.")
            commit_confirmed = st.checkbox("I reviewed reconciliation and authorize this batch commit.")
            if st.button("Commit migration batch", type="primary", disabled=not commit_confirmed):
                try:
                    result = repo.commit_migration_batch(prepared)
                    st.session_state.eims_migration_commit_result = result
                    st.success(f"Migration committed: {sum(result.get('counts', {}).values()):,} new CORE rows.")
                except Exception as exc:
                    show_data_error(exc)

    committed = st.session_state.get("eims_migration_commit_result")
    if committed and committed.get("batch_id") == analysis.batch_id:
        report = analysis.reconciliation.copy()
        report["COMMITTED_ROWS"] = report["SOURCE_ENTITY"].map(committed.get("counts", {})).fillna(0).astype(int)
        with st.container(border=True):
            section_intro("Committed reconciliation", "Source, RAW, committed, rejected and unmatched counts for this session.")
            st.dataframe(report, hide_index=True, width="stretch")

with st.container(border=True):
    section_intro("Migration history", "Workflow status is separate from daily production import status.")
    try:
        history = repo.get_migration_batches()
        if history.empty:
            st.info("No historical migration batches have been prepared.")
        else:
            st.dataframe(history, hide_index=True, width="stretch")
            if has_permission(user, Permission.DELETE_DATA):
                synthetic = history[history["MIGRATION_BATCH_ID"].astype(str).str.startswith("DEV_MIGRATION_")]
                options = synthetic["MIGRATION_BATCH_ID"].astype(str).tolist()
                selected = st.selectbox("Synthetic batch cleanup", [""] + options)
                cleanup_confirmed = st.checkbox("Delete only records mapped to the selected synthetic batch.")
                if st.button("Clean up selected synthetic batch", disabled=not selected or not cleanup_confirmed):
                    try:
                        repo.cleanup_synthetic_migration(selected)
                        st.session_state.pop("eims_prepared_batch_id", None)
                        st.success("Selected synthetic migration batch was removed.")
                        st.rerun()
                    except Exception as exc:
                        show_data_error(exc)
    except Exception as exc:
        show_data_error(exc)
