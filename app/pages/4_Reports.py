"""EFNS internal Report Center with curated reports and safe customization."""

from __future__ import annotations

import datetime as dt

import pandas as pd
import streamlit as st

from app.auth import can_current, get_auth_store, require_page_permission
from app.navigation import format_timestamp, timestamp_columns
from app.security import Permission
from app.services.report_center import (
    CUSTOM_DATASETS, build_custom_report, build_quota_summary, report_csv,
    report_definition, report_xlsx, visible_catalog,
)
from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.constants import (
    ACCOUNT_STATUSES, FACILITY_DETAIL_STATUSES, FACILITY_STATUSES,
    FARM_LOCATION_STATUSES, FLOCK_STATUSES, FLOCK_TRANSACTION_TYPES,
    QUOTA_STATUSES, QUOTA_TRANSACTION_TYPES, QUOTA_TYPES,
)
from data.repositories import get_repository


user = require_page_permission(Permission.VIEW_REPORTS)
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo

page_header("Report Center", "Run curated operational reports or build an allowlisted custom report.", "REPORTING")
section = st.radio("Report Center section", ["Report Library", "Customize Report", "Saved Reports"], horizontal=True, key="report_center_section")


def audit(action: str, report_id: str, details=None):
    get_auth_store().record_action(user, action, "REPORT", report_id, details or {})


def downloads(frame: pd.DataFrame, stem: str, report_id: str):
    if not can_current(Permission.EXPORT_REPORT):
        st.info("Your role can view this report but cannot export report data.")
        return
    left, right = st.columns(2)
    if left.download_button("Export CSV", report_csv(user, frame), f"{stem}.csv", "text/csv", width="stretch"):
        audit("EXPORT", report_id, {"format": "CSV", "row_count": len(frame)})
    if right.download_button("Export XLSX", report_xlsx(user, frame), f"{stem}.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", width="stretch"):
        audit("EXPORT", report_id, {"format": "XLSX", "row_count": len(frame)})


def template_record_selector(entity: str):
    definitions = {
        "ACCOUNT": (repo.get_accounts, "ACCOUNT_ID", "ORGANIZATION_NAME"),
        "FLOCK": (repo.get_flocks, "FLOCK_ID", "FLOCK_NUMBER"),
        "SALMONELLA_TEST": (repo.get_salmonella_tests, "SALMONELLA_TEST_ID", "PERMIT_NUMBER"),
    }
    loader, key, label = definitions[entity]
    frame = loader()
    if frame.empty:
        st.info(f"No {entity.replace('_', ' ').title()} records are available for selection.")
        return
    options = {f"{row.get(label) or row[key]} · {str(row[key])[:8]}": row[key] for row in frame.to_dict("records")}
    chosen = st.selectbox("Source record", list(options), key=f"report_template_{entity}")
    st.caption(f"Selected stable record ID: {options[chosen]}")
    st.warning("The official template, wording, branding, declarations and signatures have not been supplied. Document generation is disabled.")


if section == "Report Library":
    catalog = visible_catalog(user)
    search, category, report_type = st.columns([2, 1, 1])
    keyword = search.text_input("Search reports", placeholder="Report name or description", key="report_library_search")
    categories = sorted({item.category for item in catalog})
    category_value = category.selectbox("Category", ["All", *categories], key="report_library_category")
    types = sorted({item.report_type for item in catalog})
    type_value = report_type.selectbox("Type", ["All", *types], key="report_library_type")
    filtered = [item for item in catalog if (category_value == "All" or item.category == category_value) and (type_value == "All" or item.report_type == type_value) and (not keyword or keyword.casefold() in f"{item.name} {item.description}".casefold())]
    st.caption(f"{len(filtered)} report definition(s)")
    if not filtered:
        st.info("No reports match the current filters.")
    for item in filtered:
        with st.container(border=True):
            title, action = st.columns([5, 1])
            title.markdown(f"### {item.name}")
            title.caption(f"{item.category} · {item.report_type} · {item.status}")
            title.write(item.description)
            title.caption("Parameters: " + ", ".join(item.parameters))
            if action.button("Open", key=f"open_report_{item.report_id}", disabled=item.handler is None and item.input_entity is None, width="stretch"):
                st.session_state.report_center_open_report = item.report_id
                st.rerun()

    open_id = st.session_state.get("report_center_open_report")
    if open_id:
        definition = report_definition(open_id)
        st.divider(); section_intro(definition.name, definition.description)
        if st.button("Close report", icon=":material/arrow_back:", key="close_library_report"):
            st.session_state.pop("report_center_open_report", None); st.rerun()
        if definition.handler == "quota_summary":
            accounts = repo.get_accounts()
            account_options = {"All Accounts": None, **{f"{r.ORGANIZATION_NAME} · {r.REGISTRATION_NUMBER or str(r.ACCOUNT_ID)[:8]}": r.ACCOUNT_ID for r in accounts.itertuples()}}
            params = st.columns(4)
            as_of = params[0].date_input("As of Date", value=dt.date.today(), key="quota_summary_as_of")
            quota_type = params[1].selectbox("Quota Type", QUOTA_TYPES, key="quota_summary_type")
            account_label = params[2].selectbox("Account", list(account_options), key="quota_summary_account")
            status = params[3].selectbox("Status", ["Active", "Inactive", "Expired", "All"], key="quota_summary_status")
            st.caption("Address rule: prefer Active Farm Locations, then choose the lowest FARM_LOCATION_ID. Account phone is a fallback; Fax comes from Account. This rule is provisional.")
            if st.button("Run Report", type="primary", icon=":material/play_arrow:", key="run_quota_summary"):
                try:
                    result, metrics = build_quota_summary(repo, user=user, as_of_date=as_of, quota_type=quota_type, account_id=account_options[account_label], status=None if status == "All" else status)
                    st.session_state.quota_summary_result = result
                    st.session_state.quota_summary_metrics = metrics
                    st.session_state.quota_summary_execution = dt.datetime.now(dt.timezone.utc)
                    st.session_state.quota_summary_parameters = {
                        "as_of": as_of, "quota_type": quota_type,
                        "account": account_label, "status": status,
                    }
                    audit("RUN_REPORT", definition.report_id, {"row_count": len(result), "quota_type": quota_type})
                except Exception as exc: show_data_error(exc)
            result = st.session_state.get("quota_summary_result")
            metrics = st.session_state.get("quota_summary_metrics")
            if isinstance(result, pd.DataFrame):
                applied = st.session_state.get("quota_summary_parameters", {})
                st.markdown("## Quota Summary Report")
                st.caption(
                    f"Quota Type: {applied.get('quota_type', quota_type)} · "
                    f"As of: {applied.get('as_of', as_of)} · "
                    f"Account: {applied.get('account', account_label)} · "
                    f"Status: {applied.get('status', status)} · "
                    f"Executed: {format_timestamp(st.session_state.get('quota_summary_execution'))}"
                )
                count_col, issuance_col = st.columns(2)
                count_col.metric("Distinct Producer count", metrics["producer_count"])
                issuance_col.metric("Total Issuance", "Pending confirmation" if metrics["total_issuance"] is None else f"{metrics['total_issuance']:,.2f}")
                st.caption("Mortality is omitted because no reliable source or confirmed formula exists. Issuance is intentionally blank pending confirmation.")
                st.caption(f"{len(result):,} quota registration row(s)")
                if result.empty: st.info("No Quota Registrations match the selected parameters.")
                else: st.dataframe(result, width="stretch", hide_index=True)
                downloads(result, "quota_summary_report", definition.report_id)
        elif definition.handler == "salmonella_report":
            st.info("Use the registered Salmonella Test Report page for the existing filterable report.")
            if st.button("Open Salmonella Test Report", icon=":material/lab_profile:"):
                st.switch_page("pages/10_Salmonella_Report.py")
        elif definition.input_entity:
            template_record_selector(definition.input_entity)

elif section == "Customize Report":
    require_page_permission(Permission.USE_REPORT_BUILDER)
    dataset = st.selectbox("Dataset", list(CUSTOM_DATASETS), key="custom_report_dataset")
    _method, _id, definitions = CUSTOM_DATASETS[dataset]
    labels = {field.label: field.source for field in definitions}
    selected_labels = st.multiselect("Output columns", list(labels), default=list(labels)[:5], key="custom_report_columns")
    selected_fields = [labels[label] for label in selected_labels]

    accounts = repo.get_accounts(); farm_locations = repo.get_farm_locations(); facilities = repo.get_facilities(); flocks = repo.get_flocks()
    account_options = {"All": None, **{f"{r.ORGANIZATION_NAME} · {str(r.ACCOUNT_ID)[:8]}": r.ACCOUNT_ID for r in accounts.itertuples()}}
    farm_location_options = {"All": None, **{f"{r.LOCATION_NAME} · {str(r.FARM_LOCATION_ID)[:8]}": r.FARM_LOCATION_ID for r in farm_locations.itertuples()}}
    facility_options = {"All": None, **{f"{r.FACILITY_NAME} · {str(r.FACILITY_ID)[:8]}": r.FACILITY_ID for r in facilities.itertuples()}}
    flock_options = {"All": None, **{f"{r.FLOCK_NUMBER} · {str(r.FLOCK_ID)[:8]}": r.FLOCK_ID for r in flocks.itertuples()}}
    filters = {}
    filter_cols = st.columns(4)
    filters["account_id"] = account_options[filter_cols[0].selectbox("Account", list(account_options), key="custom_filter_account")]
    filters["facility_id"] = facility_options[filter_cols[1].selectbox("Facility", list(facility_options), key="custom_filter_facility")]
    filters["flock_id"] = flock_options[filter_cols[2].selectbox("Flock", list(flock_options), key="custom_filter_flock")]
    status_values = {"Accounts": ACCOUNT_STATUSES, "Farm Locations": FARM_LOCATION_STATUSES, "Facilities": FACILITY_STATUSES, "Facility Details": FACILITY_DETAIL_STATUSES, "Flocks": FLOCK_STATUSES, "Quota Registrations": QUOTA_STATUSES}.get(dataset, ())
    status = filter_cols[3].selectbox("Status", ["All", *status_values], disabled=not status_values, key="custom_filter_status")
    if status != "All": filters["statuses"] = (status,)
    extra = st.columns(4)
    farm_location_label = extra[0].selectbox("Farm Location", list(farm_location_options), disabled=dataset != "Farm Locations", key="custom_filter_farm_location")
    filters["farm_location_id"] = farm_location_options[farm_location_label] if dataset == "Farm Locations" else None
    quota_value = extra[1].selectbox("Quota Type", ["All", *QUOTA_TYPES], key="custom_filter_quota")
    filters["quota_type"] = None if quota_value == "All" else quota_value
    transaction_values = FLOCK_TRANSACTION_TYPES if dataset == "Flock Transactions" else QUOTA_TRANSACTION_TYPES if dataset == "Quota Transactions" else ()
    transaction_value = extra[2].selectbox("Transaction Type", ["All", *transaction_values], disabled=not transaction_values, key="custom_filter_transaction")
    filters["transaction_type"] = None if transaction_value == "All" else transaction_value
    use_dates = extra[3].checkbox("Use date range", key="custom_filter_use_dates")
    date_range = st.date_input("Date range", value=(dt.date.today() - dt.timedelta(days=365), dt.date.today()), disabled=not use_dates, key="custom_filter_dates")
    if use_dates and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        filters["date_from"], filters["date_to"] = date_range

    group_labels = st.multiselect("Group by", selected_labels, key="custom_report_group")
    group_by = [labels[label] for label in group_labels]
    numeric = [field for field in definitions if field.source in selected_fields and field.aggregations]
    aggregation_field = st.selectbox("Aggregation field", ["None", *[field.label for field in numeric]], key="custom_report_aggregate_field")
    aggregations = {}
    if aggregation_field != "None":
        field = next(field for field in numeric if field.label == aggregation_field)
        aggregations[field.source] = st.selectbox("Aggregation", field.aggregations, key="custom_report_aggregate")
    sort_label = st.selectbox("Sort by", ["None", *selected_labels], key="custom_report_sort")
    ascending = st.radio("Sort direction", ["Ascending", "Descending"], horizontal=True, key="custom_report_direction") == "Ascending"
    run, reset = st.columns(2)
    if reset.button("Reset configuration", icon=":material/restart_alt:", width="stretch"):
        for key in [key for key in st.session_state if key.startswith("custom_")]: st.session_state.pop(key, None)
        st.session_state.pop("custom_report_result", None); st.rerun()
    if run.button("Run Report", type="primary", icon=":material/play_arrow:", width="stretch"):
        try:
            result = build_custom_report(repo, user=user, dataset=dataset, selected_fields=selected_fields, filters=filters, sort_by=labels.get(sort_label), ascending=ascending, group_by=group_by, aggregations=aggregations)
            st.session_state.custom_report_result = result
            st.session_state.custom_report_configuration = {"dataset": dataset, "selected_fields": selected_fields, "filters": {key: value for key, value in filters.items() if value not in (None, "", ())}, "group_by": group_by, "aggregations": aggregations, "sort_by": labels.get(sort_label), "ascending": ascending}
            audit("RUN_REPORT", "custom-builder", {"dataset": dataset, "row_count": len(result)})
        except Exception as exc: show_data_error(exc)
    result = st.session_state.get("custom_report_result")
    if isinstance(result, pd.DataFrame):
        section_intro("Preview", f"{len(result):,} result row(s); exports contain this exact filtered result and column order.")
        if result.empty: st.info("No records match the selected configuration.")
        else: st.dataframe(result, width="stretch", hide_index=True, column_config=timestamp_columns(result.columns))
        downloads(result, "efns_custom_report", "custom-builder")
        save_name = st.text_input("Save this configuration for this session", key="custom_report_save_name")
        if st.button("Save configuration", disabled=not save_name.strip(), key="custom_report_save"):
            saved = st.session_state.setdefault("session_saved_reports", {})
            saved[save_name.strip()] = dict(st.session_state.custom_report_configuration)
            audit("SAVE_REPORT_CONFIG", "custom-builder", {"name": save_name.strip()})
            st.success("Saved for this Streamlit session only.")

else:
    st.info(
        "Saved report configurations are available only during this Streamlit session. "
        "They may disappear after a browser refresh, session timeout, or login change. "
        "They contain allowlisted settings, never SQL, and are not stored in Snowflake."
    )
    saved = st.session_state.get("session_saved_reports", {})
    if not saved:
        st.info("No report configurations have been saved in this session.")
    for name, configuration in saved.items():
        with st.container(border=True):
            st.markdown(f"**{name}**")
            st.caption(f"Dataset: {configuration['dataset']} · Fields: {len(configuration['selected_fields'])}")
            if st.button("Run saved report", key=f"run_saved_{name}"):
                try:
                    result = build_custom_report(repo, user=user, **configuration)
                    st.session_state.saved_report_result = result
                    st.session_state.saved_report_result_name = name
                    audit("RUN_REPORT", "custom-builder", {"saved_name": name, "row_count": len(result)})
                except Exception as exc:
                    show_data_error(exc)
            st.json(configuration, expanded=False)
    saved_result = st.session_state.get("saved_report_result")
    if isinstance(saved_result, pd.DataFrame):
        section_intro(
            st.session_state.get("saved_report_result_name", "Saved report"),
            f"{len(saved_result):,} result row(s) from the saved allowlisted configuration.",
        )
        if saved_result.empty:
            st.info("No records match the saved configuration.")
        else:
            st.dataframe(saved_result, width="stretch", hide_index=True, column_config=timestamp_columns(saved_result.columns))
        downloads(saved_result, "efns_saved_report", "custom-builder")
