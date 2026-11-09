"""Historical EIMS migration workspace for named-column Dataverse exports."""

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
    "Validate, preserve, reconcile, and commit the authorized historical Dataverse export.",
    "MIGRATION",
)

st.info(
    "This workflow uses the field names and relationships recovered from Jensen's "
    "named-column Dataverse exports. Unconfirmed business meanings remain documented "
    "as migration assumptions. Daily Production Import remains a separate workflow."
)

from app.services.flock_supplement_workspace import render_flock_supplement
render_flock_supplement(repo,user)
from app.services.flock_date_repair_workspace import render_flock_date_repair
render_flock_date_repair(repo,user)

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
            for upload in uploads:
                repo.archive_source_file(upload.name, upload.getvalue(), "HISTORICAL_EIMS")
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
    metrics[4].metric("Entities", len(analysis.reconciliation))
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
            st.success("All source rows passed the Dataverse export validation contract.")
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
        duplicate_status = str(duplicate.get("STATUS", "")).upper() if duplicate else ""
        retry_status = None
        if duplicate_status == "FAILED":
            retry_status = repo.get_migration_retry_status(duplicate["MIGRATION_BATCH_ID"])
            if retry_status["complete"]:
                st.info("The failed batch is complete in RAW and can be retried from Migration history below.")
            else:
                st.error(
                    "The failed batch is incomplete. Confirm the same package to safely restore only missing records."
                )
                for issue in retry_status["issues"]:
                    st.caption(issue)
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
        if duplicate_status == "FAILED" and retry_status and not retry_status["complete"]:
            repair_confirmed = st.checkbox(
                "I confirm this is the same package and authorize restoring missing migration records.",
                key=f"repair_confirm_{analysis.batch_id}",
            )
            if st.button(
                "Restore missing batch records",
                disabled=not repair_confirmed,
                key=f"repair_batch_{analysis.batch_id}",
            ):
                try:
                    missing_files = set(retry_status["missing_files"])
                    file_rows = []
                    for source in analysis.files:
                        stage_path = None
                        if source["SOURCE_FILENAME"] in missing_files:
                            stage_path = repo.stage_migration_file(
                                analysis.batch_id, source["SOURCE_FILENAME"], source["CONTENT"]
                            )
                        file_rows.append({**source, "STAGE_PATH": stage_path})
                    repo.repair_migration_batch(
                        {
                            "MIGRATION_BATCH_ID": analysis.batch_id,
                            "PACKAGE_HASH": analysis.package_hash,
                            "SCHEMA_VERSION": analysis.schema_version,
                        },
                        file_rows,
                        analysis.raw_rows,
                    )
                    st.session_state.eims_prepared_batch_id = analysis.batch_id
                    st.success("Missing records were restored. The failed batch is ready to retry.")
                except Exception as exc:
                    show_data_error(exc)

    prepared = st.session_state.get("eims_prepared_batch_id")
    if prepared == analysis.batch_id:
        with st.container(border=True):
            section_intro(
                "Commit Ready rows",
                "Ready rows are written to CORE in dependency order. "
                "Rejected rows remain preserved in RAW, and any write failure rolls "
                "back the target transaction.",
            )
            commit_confirmed = st.checkbox("I reviewed reconciliation and authorize this batch commit.")
            if st.button("Commit migration batch", type="primary", disabled=not commit_confirmed):
                try:
                    result = repo.commit_migration_batch(prepared)
                    st.session_state.eims_migration_commit_result = result
                    st.success(
                        f"Migration committed: "
                        f"{sum(result.get('counts', {}).values()):,} new target rows."
                    )
                except Exception as exc:
                    show_data_error(exc)

    committed = st.session_state.get("eims_migration_commit_result")
    if committed and committed.get("batch_id") == analysis.batch_id:
        report = analysis.reconciliation.copy()
        report["COMMITTED_ROWS"] = report["SOURCE_ENTITY"].map(committed.get("counts", {})).fillna(0).astype(int)
        with st.container(border=True):
            section_intro(
                "Committed reconciliation",
                "Source, RAW, inserted, rejected, and unmatched counts for this session.",
            )
            st.dataframe(report, hide_index=True, width="stretch")

with st.container(border=True):
    section_intro("Migration history", "Workflow status is separate from daily production import status.")
    try:
        history = repo.get_migration_batches()
        if history.empty:
            st.info("No historical migration batches have been prepared.")
        else:
            st.dataframe(history, hide_index=True, width="stretch")
            selected_history = st.selectbox(
                "Batch reconciliation",
                [""] + history["MIGRATION_BATCH_ID"].astype(str).tolist(),
            )
            if selected_history:
                reconciliation = repo.get_migration_reconciliation(selected_history)
                if reconciliation.empty:
                    st.info("No persisted reconciliation is available for this batch.")
                else:
                    st.dataframe(reconciliation, hide_index=True, width="stretch")

                selected_batch = history[
                    history["MIGRATION_BATCH_ID"].astype(str) == selected_history
                ].iloc[0]
                batch_status = str(selected_batch["STATUS"]).upper()
                commit_errors = repo.get_migration_commit_errors(selected_history)
                if not commit_errors.empty:
                    if batch_status == "COMMITTED":
                        st.caption("Historical failed attempts retained for audit.")
                    else:
                        st.warning("The latest migration attempt failed after validation.")
                    st.dataframe(commit_errors, hide_index=True, width="stretch")

                if batch_status in {"READY", "PARTIAL"} and not reconciliation.empty:
                    st.info(
                        "This batch is preserved in RAW. "
                        "Commit writes only Ready rows to CORE; "
                        "rejected rows remain in RAW."
                    )
                    resume_confirmed = st.checkbox(
                        "I reviewed this saved batch and authorize committing its Ready rows.",
                        key=f"resume_confirm_{selected_history}",
                    )
                    if st.button(
                        "Commit saved batch",
                        type="primary",
                        disabled=not resume_confirmed,
                        key=f"resume_commit_{selected_history}",
                    ):
                        try:
                            result = repo.commit_migration_batch(selected_history)
                            inserted = sum(result.get("counts", {}).values())
                            st.success(
                                f"Migration committed: {inserted:,} new target rows."
                            )
                            st.dataframe(
                                repo.get_migration_reconciliation(selected_history),
                                hide_index=True,
                                width="stretch",
                            )
                        except Exception as exc:
                            show_data_error(exc)
                elif batch_status == "FAILED":
                    retry_status = repo.get_migration_retry_status(selected_history)
                    if retry_status["complete"]:
                        st.warning(
                            "The previous CORE write was rolled back. Saved RAW data, rejected rows, "
                            "and migration tracking are complete and available for a safe retry."
                        )
                        retry_confirmed = st.checkbox(
                            "I reviewed this failed batch and authorize retrying its Ready rows.",
                            key=f"retry_confirm_{selected_history}",
                        )
                        if st.button(
                            "Retry migration",
                            type="primary",
                            disabled=not retry_confirmed,
                            key=f"retry_migration_{selected_history}",
                        ):
                            try:
                                result = repo.commit_migration_batch(selected_history)
                                st.session_state.eims_migration_commit_result = result
                                inserted = sum(result.get("counts", {}).values())
                                st.success(f"Migration committed: {inserted:,} new target rows.")
                                st.dataframe(
                                    repo.get_migration_reconciliation(selected_history),
                                    hide_index=True,
                                    width="stretch",
                                )
                            except Exception as exc:
                                show_data_error(exc)
                    else:
                        st.error(
                            "This failed batch is incomplete and cannot be retried yet. "
                            "Upload the same complete package above to restore missing records."
                        )
                        for issue in retry_status["issues"]:
                            st.caption(issue)
                elif batch_status == "COMMITTED":
                    st.success("This batch has already been committed.")
                    correction_status = repo.get_historical_correction_status(selected_history)
                    correction_committed = bool(
                        correction_status
                        and str(correction_status.get("STATUS", "")).upper()
                        in {"COMMITTED", "COMMITTED_WITH_PENDING"}
                    )
                    if correction_committed:
                        st.success(
                            "Correction batch committed: "
                            f"{int(correction_status.get('READY_ROW_COUNT') or 0):,} CORE records; "
                            f"{int(correction_status.get('PENDING_ROW_COUNT') or 0):,} recorded for review at that commit. "
                            f"Committed at {correction_status.get('COMMITTED_AT')}."
                        )
                    st.info(
                        "Confirmed historical exceptions can be reviewed in a separate correction batch. "
                        "The original batch, rejected rows, and source values remain unchanged."
                    )
                    if st.button(
                        "Prepare correction preview",
                        key=f"preview_corrections_{selected_history}",
                    ):
                        try:
                            st.session_state.eims_correction_preview = (
                                repo.preview_historical_correction_review(selected_history)
                            )
                        except Exception as exc:
                            show_data_error(exc)
                    correction_preview = st.session_state.get("eims_correction_preview")
                    if correction_preview and correction_preview.batch_id == selected_history:
                        from app.services.historical_correction_workspace import render_correction_editor
                        render_correction_editor(repo,correction_preview,has_permission(user,Permission.IMPORT_DATA))
                        correction_frame = correction_preview.review_frame.copy()
                        correction_frame["ORIGINAL_VALIDATION_MESSAGES"] = correction_frame[
                            "ORIGINAL_VALIDATION_MESSAGES"
                        ].map(lambda messages: " | ".join(messages))
                        correction_frame["CURRENT_VALIDATION_MESSAGES"] = correction_frame[
                            "CURRENT_VALIDATION_MESSAGES"
                        ].map(lambda messages: " | ".join(messages))
                        correction_metrics = st.columns(4)
                        correction_metrics[0].metric("Committed to CORE", len(correction_preview.committed_rows))
                        correction_metrics[1].metric("Eligible for CORE", len(correction_preview.core_rows))
                        correction_metrics[2].metric("Needs confirmation", len(correction_preview.pending_rows))
                        correction_metrics[3].metric("Original rejected rows", len(correction_preview.rows))
                        st.dataframe(correction_preview.summary, hide_index=True, width="stretch")
                        review_filter = st.selectbox(
                            "Correction rows",
                            ("Needs confirmation", "Eligible for CORE", "Committed to CORE", "All rows"),
                            key=f"correction_filter_{selected_history}",
                        )
                        if review_filter == "Needs confirmation":
                            review_frame = correction_frame[
                                correction_frame["DISPOSITION"] == "PENDING_CONFIRMATION"
                            ]
                        elif review_filter == "Eligible for CORE":
                            review_frame = correction_frame[
                                correction_frame["DISPOSITION"] == "READY_CORE"
                            ]
                        elif review_filter == "Committed to CORE":
                            review_frame = correction_frame[
                                correction_frame["DISPOSITION"] == "ALREADY_COMMITTED"
                            ]
                        else:
                            review_frame = correction_frame
                        entities = review_frame["SOURCE_ENTITY"].drop_duplicates().tolist()
                        if not entities:
                            st.info("No correction rows match this view.")
                        else:
                            tabs = st.tabs(entities)
                            source_columns = [
                                "SOURCE_FILENAME", "SOURCE_ROW_NUMBER", "MIGRATION_RAW_ROW_ID",
                                "SOURCE_ID", "TARGET_ID", "RELATION_STATUS", "REASON",
                                "ORIGINAL_VALIDATION_MESSAGES",
                                "CURRENT_VALIDATION_MESSAGES",
                            ]
                            for tab, entity in zip(tabs, entities):
                                with tab:
                                    entity_frame = review_frame[
                                        review_frame["SOURCE_ENTITY"] == entity
                                    ].drop(columns=["SOURCE_ENTITY", "DISPOSITION"])
                                    visible_business = [
                                        column for column in entity_frame.columns
                                        if column not in source_columns
                                        and not entity_frame[column].isna().all()
                                    ]
                                    st.caption(f"{len(entity_frame):,} row(s)")
                                    st.dataframe(
                                        entity_frame[[*source_columns, *visible_business]],
                                        hide_index=True,
                                        width="stretch",
                                    )
                        st.download_button(
                            "Download correction preview",
                            correction_frame.to_csv(index=False).encode("utf-8-sig"),
                            file_name=f"{selected_history}_correction_preview.csv",
                            mime="text/csv",
                            key=f"download_corrections_{selected_history}",
                        )
                        if correction_preview.core_rows:
                            correction_confirmed = st.checkbox(
                                "I reviewed this separate correction batch and authorize the eligible records.",
                                key=f"confirm_corrections_{correction_preview.review_token}",
                            )
                            if st.button(
                                "Commit eligible corrections",
                                type="primary",
                                disabled=not correction_confirmed,
                                key=f"commit_corrections_{selected_history}",
                            ):
                                try:
                                    repo.commit_historical_correction_review(selected_history,correction_preview.review_token)
                                    st.session_state.pop("eims_correction_preview", None)
                                    st.rerun()
                                except Exception as exc:
                                    show_data_error(exc)

            if has_permission(user, Permission.DELETE_DATA):
                st.caption("Automatic migration cleanup is unavailable. Historical source and correction records are retained.")
    except Exception as exc:
        show_data_error(exc)
