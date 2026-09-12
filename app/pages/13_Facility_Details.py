"""Enterprise Facility Detail list and record workspace."""

from __future__ import annotations

import streamlit as st

from app.navigation import current_page_url, ensure_record_form_state, format_timestamp, list_command_bar, module_url, open_view, read_record_view, record_command_bar, selected_row_index
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro, show_data_error
from data.repositories import get_repository
from data.repositories.base import RepositoryError


apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
view = read_record_view()
details = repo.get_facility_details()
facilities = repo.get_facilities()
accounts = repo.get_accounts()
account_names = {row.ACCOUNT_ID: row.ORGANIZATION_NAME for row in accounts.itertuples()}
facility_names = {row.FACILITY_ID: row.FACILITY_NAME for row in facilities.itertuples()}
facility_accounts = {row.FACILITY_ID: row.ACCOUNT_ID for row in facilities.itertuples()}
facility_options = {f"{row.FACILITY_NAME} · {account_names.get(row.ACCOUNT_ID, 'Unknown')}": row.FACILITY_ID for row in facilities.itertuples()}


def option_index(options, value):
    return options.index(value) if value in options else 0


def label_for_id(mapping, value):
    return next((label for label, record_id in mapping.items() if record_id == value), next(iter(mapping), None))


if view.name == "list":
    page_header("Facility Details", "Maintain the existing provisional detail records associated with Facilities.", "FACILITY MANAGEMENT")
    selected_index = selected_row_index("facility_detail_list_grid")
    row_ids = st.session_state.get("facility_detail_list_row_ids", [])
    selected_id = row_ids[selected_index] if selected_index is not None and selected_index < len(row_ids) else None
    action = list_command_bar("facility_detail_list", selected=bool(selected_id))
    if action == "new": open_view("new")
    if action == "refresh": st.rerun()
    if action == "delete" and selected_id: st.session_state.facility_detail_delete_pending = selected_id
    if st.session_state.get("facility_detail_delete_pending"):
        with st.container(border=True):
            st.warning("Delete the selected Facility Detail? A referencing Flock will block deletion.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", icon=":material/delete:", key="facility_detail_confirm_delete"):
                    try:
                        repo.delete_facility_detail(st.session_state.facility_detail_delete_pending)
                        st.session_state.pop("facility_detail_delete_pending", None); st.rerun()
                    except (ValueError, RepositoryError) as exc: show_data_error(exc)
                if st.button("Cancel", key="facility_detail_cancel_delete"):
                    st.session_state.pop("facility_detail_delete_pending", None); st.rerun()
    search_row = st.columns([5, 1])
    keyword = search_row[0].text_input("Search", placeholder="Detail, facility or account", key="facility_detail_filter_keyword")
    with search_row[1]:
        st.write("")
        if st.button("Reset Filters", icon=":material/filter_alt_off:", key="facility_detail_reset", width="stretch"):
            clear_widget_prefix("facility_detail_filter_"); st.rerun()
    facility_filter = st.selectbox("Facility", ["All", *facility_options], key="facility_detail_filter_facility")
    display = repo.get_facility_details(facility_options.get(facility_filter)).copy()
    if not display.empty:
        display["FACILITY_NAME"] = display["FACILITY_ID"].map(facility_names)
        display["ACCOUNT_ID"] = display["FACILITY_ID"].map(facility_accounts)
        display["ACCOUNT_NAME"] = display["ACCOUNT_ID"].map(account_names)
        if keyword:
            columns = ["DETAIL_NAME", "DETAIL_TYPE", "FACILITY_NAME", "ACCOUNT_NAME"]
            display = display[display[columns].fillna("").astype(str).apply(lambda column: column.str.contains(keyword, case=False, regex=False)).any(axis=1)]
    st.caption(f"{len(display):,} facility detail(s)")
    if display.empty:
        st.info("No Facility Details match the current filters.")
    else:
        display = display.reset_index(drop=True)
        display["DETAIL_LINK"] = display.apply(lambda row: current_page_url(row["FACILITY_DETAIL_ID"], row["DETAIL_NAME"]), axis=1)
        display["FACILITY_LINK"] = display.apply(lambda row: module_url("Facilities", row["FACILITY_ID"], row["FACILITY_NAME"]), axis=1)
        display["ACCOUNT_LINK"] = display.apply(lambda row: module_url("Accounts_&_Facilities", row["ACCOUNT_ID"], row["ACCOUNT_NAME"]), axis=1)
        st.session_state.facility_detail_list_row_ids = display["FACILITY_DETAIL_ID"].tolist()
        st.dataframe(display[["DETAIL_LINK", "FACILITY_LINK", "ACCOUNT_LINK", "DETAIL_TYPE", "STATUS", "COMMENTS", "CREATED_AT"]], width="stretch", height=520, hide_index=True, on_select="rerun", selection_mode="single-row", key="facility_detail_list_grid", column_config={"DETAIL_LINK": st.column_config.LinkColumn("Facility Detail", display_text=r".*#(.*)$"), "FACILITY_LINK": st.column_config.LinkColumn("Facility", display_text=r".*#(.*)$"), "ACCOUNT_LINK": st.column_config.LinkColumn("Account", display_text=r".*#(.*)$"), "CREATED_AT": st.column_config.DatetimeColumn("Created On", format="YYYY-MM-DD HH:mm")})
else:
    current = repo.get_facility_detail(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        page_header("Facility Detail Not Found", "The requested record does not exist or is no longer available.", "FACILITY MANAGEMENT")
        if st.button("Back to Facility Details", icon=":material/arrow_back:"): open_view("list")
        st.stop()
    is_form = view.name in {"new", "edit"}
    page_header("New Facility Detail" if view.name == "new" else current.get("DETAIL_NAME") or "Facility Detail", "Facility relationship and existing provisional detail fields.", "FACILITY DETAIL")
    action = record_command_bar("facility_detail_record", view.name)
    if action in {"back", "cancel"}: open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "refresh": st.rerun()
    if action == "edit": clear_widget_prefix("facility_detail_form_"); open_view("edit", view.record_id)
    if action == "delete" and view.record_id:
        try: repo.delete_facility_detail(view.record_id); open_view("list")
        except (ValueError, RepositoryError) as exc: show_data_error(exc)
    if not is_form:
        facility_id = current.get("FACILITY_ID")
        account_id = facility_accounts.get(facility_id)
        st.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))} · Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary, related = st.tabs(["Summary", "Related Records"])
        with summary:
            with st.container(border=True):
                left, right = st.columns(2)
                left.markdown(f"**Detail Name**  \n{current.get('DETAIL_NAME') or '—'}")
                left.markdown(f"**Detail Type**  \n{current.get('DETAIL_TYPE') or '—'}")
                left.markdown(f"**Status**  \n{current.get('STATUS') or '—'}")
                right.markdown(f"**Facility**  \n[{facility_names.get(facility_id, 'Unknown')}]({module_url('Facilities', facility_id, facility_names.get(facility_id, 'Unknown'))})")
                if account_id: right.markdown(f"**Account**  \n[{account_names.get(account_id, 'Unknown')}]({module_url('Accounts_&_Facilities', account_id, account_names.get(account_id, 'Unknown'))})")
                right.markdown(f"**Comments**  \n{current.get('COMMENTS') or 'No comments.'}")
        with related:
            section_intro("Flocks")
            flocks = repo.get_flocks(facility_id=facility_id)
            if "FACILITY_DETAIL_ID" in flocks: flocks = flocks[flocks["FACILITY_DETAIL_ID"] == view.record_id]
            if flocks.empty: st.info("No Flocks reference this Facility Detail.")
            else:
                flocks = flocks.copy(); flocks["FLOCK_LINK"] = flocks.apply(lambda row: module_url("Flocks", row["FLOCK_ID"], row["FLOCK_NUMBER"]), axis=1)
                st.dataframe(flocks[["FLOCK_LINK", "PERMIT_NUMBER", "BIRD_COUNT", "STATUS"]], width="stretch", hide_index=True, column_config={"FLOCK_LINK": st.column_config.LinkColumn("Flock", display_text=r".*#(.*)$")})
    else:
        current = current or {}
        if facilities.empty:
            st.error("Create a Facility before creating a Facility Detail."); st.stop()
        ensure_record_form_state("facility_detail_form_", view.record_id)
        expected_key = f"facility_detail_form_expected_{view.record_id}"
        if view.name == "edit": st.session_state.setdefault(expected_key, current.get("UPDATED_AT"))
        requested_facility = st.query_params.get("facility_id")
        facility_id = current.get("FACILITY_ID") or (str(requested_facility) if requested_facility in set(facility_options.values()) else None)
        with st.container(border=True):
            left, right = st.columns(2)
            facility_label = left.selectbox("Facility *", list(facility_options), index=option_index(list(facility_options), label_for_id(facility_options, facility_id)), key="facility_detail_form_facility")
            selected_facility_id = facility_options[facility_label]
            left.text_input("Account", value=account_names.get(facility_accounts.get(selected_facility_id), "Unknown"), disabled=True, key="facility_detail_form_account")
            detail_name = left.text_input("Detail Name *", value=str(current.get("DETAIL_NAME") or ""), key="facility_detail_form_name")
            detail_type = right.text_input("Detail Type", value=str(current.get("DETAIL_TYPE") or ""), key="facility_detail_form_type")
            status = right.text_input("Status", value=str(current.get("STATUS") or ""), key="facility_detail_form_status")
            comments = right.text_area("Comments", value=str(current.get("COMMENTS") or ""), key="facility_detail_form_comments")
        if action == "save":
            if not detail_name.strip(): st.error("Detail Name is required.")
            else:
                record = {"FACILITY_DETAIL_ID": view.record_id, "FACILITY_ID": selected_facility_id, "DETAIL_NAME": detail_name.strip(), "DETAIL_TYPE": detail_type.strip() or None, "STATUS": status.strip() or None, "COMMENTS": comments.strip() or None}
                if not view.record_id: record.pop("FACILITY_DETAIL_ID")
                else: record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_key)
                try:
                    saved_id = repo.upsert_facility_detail(record)
                    clear_widget_prefix("facility_detail_form_"); open_view("detail", saved_id)
                except (ValueError, RepositoryError) as exc: show_data_error(exc)
