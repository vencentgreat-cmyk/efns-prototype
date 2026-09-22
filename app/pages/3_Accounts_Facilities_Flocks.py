"""Enterprise account list, record detail, new and edit workspace."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.auth import require_operational_page
from app.navigation import (
    format_timestamp,
    list_command_bar,
    open_module,
    open_view,
    read_record_view,
    record_command_bar,
    saved_view_selector,
    selected_row_index,
    timestamp_column,
)
from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro, show_data_error
from data.constants import ACCOUNT_ROLE_FIELDS, ACCOUNT_STATUSES
from data.repositories import get_repository
from data.repositories.base import RepositoryError


require_operational_page()
apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()
repo = st.session_state.repo
view = read_record_view()

PROVINCES = ("NS", "NB", "PE", "NL", "QC", "ON", "MB", "SK", "AB", "BC", "YT", "NT", "NU", "Other")
ROLE_FIELDS = (
    ("BREEDER_ROLE", "Breeder"),
    ("HATCHERY_ROLE", "Hatchery"),
    ("PULLET_GROWER_ROLE", "Pullet Grower"),
    ("PRODUCER_ROLE", "Producer"),
    ("GRADER_ROLE", "Grader"),
    ("PROCESSOR_BREAKER_ROLE", "Processor/Breaker"),
    ("DISPOSAL_PLANT_ROLE", "Disposal Plant"),
    ("UNREGULATED_ROLE", "Unregulated"),
    ("PROV_BOARD_EFC_ROLE", "Prov Board/EFC"),
    ("GOVERNMENT_ROLE", "Government"),
    ("VENDOR_ROLE", "Vendor"),
    ("RESEARCH_EXEMPT_ROLE", "Research Exempt"),
    ("SHIPPER_ROLE", "Shipper"),
    ("OTHER_ROLE", "Other"),
)


def option_index(options, value, default=0):
    return options.index(value) if value in options else default


def account_lookup(accounts: pd.DataFrame, current_id=None):
    result = {"Not selected": None}
    for row in accounts.itertuples():
        if row.ACCOUNT_ID != current_id:
            result[f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}"] = row.ACCOUNT_ID
    return result


def lookup_label(options, value):
    return next((label for label, item_id in options.items() if item_id == value), "Not selected")


accounts = repo.get_accounts()


if view.name == "list":
    page_header("Accounts", "Search and maintain organization, registration, contact, address and role records.", "ACCOUNT MANAGEMENT")
    warning = st.session_state.pop("account_list_warning", None)
    if warning:
        st.warning(warning)

    statuses, role_view = saved_view_selector(
        "ACCOUNT", "Accounts", key="account_saved_view", role_views=ACCOUNT_ROLE_FIELDS,
        selection_keys=("account_list_grid", "account_list_row_ids", "account_selected_id", "account_delete_pending"),
    )
    selected_index = selected_row_index("account_list_grid")
    selected_id = None
    prior_rows = st.session_state.get("account_list_row_ids", [])
    if selected_index is not None and selected_index < len(prior_rows):
        selected_id = prior_rows[selected_index]
    if selected_id:
        st.session_state["account_selected_id"] = selected_id
    else:
        st.session_state.pop("account_selected_id", None)

    action = list_command_bar("account_list", selected=bool(selected_id))
    if action == "view" and selected_id:
        open_view("detail", selected_id)
    if action == "new":
        open_view("new")
    if action == "refresh":
        clear_widget_prefix("account_filter_")
        st.rerun()
    if action == "delete" and selected_id:
        st.session_state.account_delete_pending = selected_id

    pending_delete = st.session_state.get("account_delete_pending")
    if pending_delete:
        pending = repo.get_account(pending_delete)
        if pending:
            with st.container(border=True):
                st.warning(f"Delete Account “{pending.get('ORGANIZATION_NAME')}”? Referenced Accounts cannot be deleted.")
                with st.container(horizontal=True):
                    if st.button("Confirm delete", type="primary", icon=":material/delete:", key="account_confirm_delete"):
                        try:
                            repo.delete_account(pending_delete)
                            st.session_state.pop("account_delete_pending", None)
                            st.rerun()
                        except (ValueError, RepositoryError) as exc:
                            show_data_error(exc)
                    if st.button("Cancel", key="account_cancel_delete"):
                        st.session_state.pop("account_delete_pending", None)
                        st.rerun()

    filter_columns = st.columns([2, 1])
    keyword = filter_columns[0].text_input("Filter by keyword", placeholder="Name, registration, city, phone or email", key="account_filter_keyword")
    role_options = ["All", *[label for _, label in ROLE_FIELDS]]
    role_filter = filter_columns[1].selectbox("Additional role filter", role_options, key="account_filter_role")

    filtered = repo.get_accounts(statuses=statuses, role_field=role_view, keyword=keyword or None)
    if role_filter != "All":
        role_column = next(field for field, label in ROLE_FIELDS if label == role_filter)
        if role_column in filtered:
            filtered = filtered[filtered[role_column].fillna(False).astype(bool)]

    if filtered.empty:
        st.info("No Accounts match the current filters.")
    else:
        display = filtered.copy().reset_index(drop=True)
        st.session_state.account_list_row_ids = display["ACCOUNT_ID"].tolist()
        st.caption(f"{len(display):,} Account(s) in this view")
        st.dataframe(
            display[["ORGANIZATION_NAME", "REGISTRATION_NUMBER", "CITY", "PROVINCE", "POSTAL_CODE", "CONTACT_PHONE", "CONTACT_EMAIL", "STATUS", "CREATED_AT"]],
            width="stretch",
            height=540,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="account_list_grid",
            column_config={
                "ORGANIZATION_NAME": st.column_config.TextColumn("Account Name", width="large"),
                "REGISTRATION_NUMBER": "Registration Number",
                "CONTACT_PHONE": "Main Phone",
                "CONTACT_EMAIL": "Email",
                "CREATED_AT": timestamp_column("Created On"),
            },
        )

else:
    current = repo.get_account(view.record_id) if view.record_id else None
    if view.name in {"detail", "edit"} and current is None:
        st.session_state["account_list_warning"] = "The selected Account no longer exists. The list has been refreshed."
        st.session_state.pop("account_selected_id", None)
        open_view("list")

    is_form = view.name in {"new", "edit"}
    title = "New Account" if view.name == "new" else current["ORGANIZATION_NAME"]
    subtitle = "Create a complete Account record." if view.name == "new" else f"Registration {current.get('REGISTRATION_NUMBER') or 'not assigned'}"
    page_header(title, subtitle, "ACCOUNT RECORD")
    action = record_command_bar("account_record", view.name)
    if action in {"back", "cancel"}:
        if action == "back":
            st.session_state.pop("account_selected_id", None)
            st.session_state.pop("account_list_grid", None)
        open_view("detail", view.record_id) if action == "cancel" and view.record_id else open_view("list")
    if action == "edit":
        clear_widget_prefix("account_form_")
        open_view("edit", view.record_id)
    if action == "delete" and view.record_id:
        st.session_state.account_record_delete_pending = True

    if st.session_state.get("account_record_delete_pending"):
        with st.container(border=True):
            st.warning("This action permanently removes the Account when no related records reference it.")
            with st.container(horizontal=True):
                if st.button("Confirm delete", type="primary", icon=":material/delete:", key="account_record_confirm"):
                    try:
                        repo.delete_account(view.record_id)
                        st.session_state.pop("account_record_delete_pending", None)
                        open_view("list")
                    except (ValueError, RepositoryError) as exc:
                        show_data_error(exc)
                if st.button("Keep Account", key="account_record_keep"):
                    st.session_state.pop("account_record_delete_pending", None)
                    st.rerun()

    if not is_form:
        audit_left, audit_right = st.columns(2)
        audit_left.caption(f"Created On: {format_timestamp(current.get('CREATED_AT'))}")
        audit_right.caption(f"Updated On: {format_timestamp(current.get('UPDATED_AT'))}")
        summary_tab, related_tab = st.tabs(["Summary", "Related Records"])
        with summary_tab:
            section_intro("Account Information")
            with st.container(border=True):
                left, middle, right = st.columns(3)
                left.markdown(f"**Account Name**  \n{current.get('ORGANIZATION_NAME') or '—'}")
                left.markdown(f"**Registration Number**  \n{current.get('REGISTRATION_NUMBER') or '—'}")
                left.markdown(f"**Status**  \n{current.get('STATUS') or '—'}")
                middle.markdown(f"**Email**  \n{current.get('CONTACT_EMAIL') or '—'}")
                middle.markdown(f"**Phone**  \n{current.get('CONTACT_PHONE') or '—'}")
                middle.markdown(f"**Website**  \n{current.get('WEBSITE') or '—'}")
                right.markdown(f"**Province of Registration**  \n{current.get('PROVINCE_OF_REGISTRATION') or '—'}")
                right.markdown(f"**Default on Reports**  \n{'Yes' if current.get('DEFAULT_ON_REPORTS') else 'No'}")
                right.markdown(f"**No SVG**  \n{'Yes' if current.get('NO_SVG') else 'No'}")
            section_intro("Address")
            with st.container(border=True):
                st.write(" · ".join(str(value) for value in (current.get("ADDRESS_LINE1"), current.get("ADDRESS_LINE2"), current.get("ADDRESS_LINE3"), current.get("CITY"), current.get("PROVINCE"), current.get("POSTAL_CODE"), current.get("COUNTRY_REGION")) if value) or "No address recorded")
                st.caption(f"Latitude: {current.get('LATITUDE') or '—'} · Longitude: {current.get('LONGITUDE') or '—'}")
            section_intro("Account Roles")
            with st.container(border=True, horizontal=True):
                active_roles = [label for field, label in ROLE_FIELDS if current.get(field)]
                st.write(" · ".join(active_roles) if active_roles else "No roles selected")
            if current.get("DESCRIPTION"):
                section_intro("Description")
                st.write(current["DESCRIPTION"])

        with related_tab:
            farm_locations = repo.get_farm_locations(account_id=view.record_id)
            facilities = repo.get_facilities(account_id=view.record_id)
            facility_details = repo.get_facility_details(account_id=view.record_id)
            flocks = repo.get_flocks(account_id=view.record_id)
            flock_transactions = repo.get_flock_transactions(account_id=view.record_id)
            related = (
                ("Farm Locations", farm_locations, "FARM_LOCATION_ID", "LOCATION_NAME", "Farm_Locations"),
                ("Facilities", facilities, "FACILITY_ID", "FACILITY_NAME", "Facilities"),
                ("Facility Details", facility_details, "FACILITY_DETAIL_ID", "DETAIL_NAME", "Facility_Details"),
                ("Flocks", flocks, "FLOCK_ID", "FLOCK_NUMBER", "Flocks"),
                ("Flock Transactions", flock_transactions, "FLOCK_TRANSACTION_ID", "TRANSACTION_TYPE", "Flock_Transactions"),
                ("Quota Registrations", repo.get_quota_registrations(account_id=view.record_id), "QUOTA_ID", "QUOTA_NAME", "Quota_Registrations"),
                ("Quota Transactions", repo.get_quota_transactions(account_id=view.record_id), "QUOTA_TRANSACTION_ID", "TRANSACTION_TYPE", "Quota_Transactions"),
                ("Salmonella Tests", repo.get_salmonella_tests(account_id=view.record_id), "SALMONELLA_TEST_ID", "PERMIT_NUMBER", "Salmonella_Tests"),
            )
            for heading, frame, id_column, label_column, slug in related:
                section_intro(f"{heading} ({len(frame.drop_duplicates(id_column)) if id_column in frame else 0})")
                if frame.empty:
                    st.info(f"No related {heading}.")
                else:
                    related_display = frame.drop_duplicates(id_column).copy().reset_index(drop=True)
                    related_display["RECORD"] = related_display.apply(lambda row: row.get(label_column) or row[id_column], axis=1)
                    columns = ["RECORD", *[column for column in frame.columns if column not in {id_column, "CREATED_AT", "UPDATED_AT"}][:5]]
                    grid_key = f"account_related_{slug}"
                    st.dataframe(related_display[columns], width="stretch", hide_index=True, on_select="rerun", selection_mode="single-row", key=grid_key)
                    related_index = selected_row_index(grid_key)
                    if related_index is not None and related_index < len(related_display):
                        if st.button(f"View selected {heading[:-1] if heading.endswith('s') else heading}", key=f"account_related_open_{slug}"):
                            open_module(slug, "detail", str(related_display.iloc[related_index][id_column]))
            production = repo.get_production_records(account_id=view.record_id).drop_duplicates("PRODUCTION_ID")
            section_intro(f"Matched Production Records ({len(production)})")
            if production.empty:
                st.info("No matched Production Records.")
            else:
                st.dataframe(production, width="stretch", hide_index=True)

    else:
        current = current or {}
        # Snapshot the version stamp when the edit form opens so a concurrent
        # save by another user is detected on submit (optimistic locking).
        expected_stamp_key = f"account_form_expected_{view.record_id}"
        if view.name == "edit" and view.record_id:
            st.session_state.setdefault(expected_stamp_key, current.get("UPDATED_AT"))
        lookup_options = account_lookup(accounts, view.record_id)
        summary_tab, address_tab, roles_tab = st.tabs(["Account Information", "Address", "Account Roles"])
        with summary_tab:
            with st.container(border=True):
                left, right = st.columns(2)
                account_name = left.text_input("Account Name *", value=str(current.get("ORGANIZATION_NAME") or ""), key="account_form_name")
                email = left.text_input("Email", value=str(current.get("CONTACT_EMAIL") or ""), key="account_form_email")
                phone = left.text_input("Phone", value=str(current.get("CONTACT_PHONE") or ""), key="account_form_phone")
                fax = left.text_input("Fax", value=str(current.get("FAX") or ""), key="account_form_fax")
                website = left.text_input("Website", value=str(current.get("WEBSITE") or ""), placeholder="https://", key="account_form_website")
                registration = left.text_input("Registration Number", value=str(current.get("REGISTRATION_NUMBER") or ""), key="account_form_registration")
                province_registration = left.selectbox("Province of Registration", PROVINCES, index=option_index(list(PROVINCES), current.get("PROVINCE_OF_REGISTRATION") or "NS"), key="account_form_province_registration")
                parent_label = right.selectbox("Parent Account", list(lookup_options), index=option_index(list(lookup_options), lookup_label(lookup_options, current.get("PARENT_ACCOUNT_ID"))), key="account_form_parent")
                grading_label = right.selectbox("Grading Station", list(lookup_options), index=option_index(list(lookup_options), lookup_label(lookup_options, current.get("GRADING_STATION_ACCOUNT_ID"))), key="account_form_grading")
                pullet_label = right.selectbox("Pullet Grower Account", list(lookup_options), index=option_index(list(lookup_options), lookup_label(lookup_options, current.get("PULLET_GROWER_ACCOUNT_ID"))), key="account_form_pullet")
                spent_fowl_plans = right.text_area("Spent Fowl Plans", value=str(current.get("SPENT_FOWL_PLANS") or ""), key="account_form_spent_fowl")
                default_reports = right.checkbox("Default on Reports", value=bool(current.get("DEFAULT_ON_REPORTS")), key="account_form_default_reports")
                no_svg = right.checkbox("No SVG", value=bool(current.get("NO_SVG")), key="account_form_no_svg")
                status = right.selectbox("Status", ACCOUNT_STATUSES, index=option_index(list(ACCOUNT_STATUSES), current.get("STATUS")), key="account_form_status")
                description = right.text_area("Description", value=str(current.get("DESCRIPTION") or ""), key="account_form_description")
        with address_tab:
            with st.container(border=True):
                left, right = st.columns(2)
                street1 = left.text_input("Address 1: Street 1", value=str(current.get("ADDRESS_LINE1") or ""), key="account_form_street1")
                street2 = left.text_input("Address 1: Street 2", value=str(current.get("ADDRESS_LINE2") or ""), key="account_form_street2")
                street3 = left.text_input("Address 1: Street 3", value=str(current.get("ADDRESS_LINE3") or ""), key="account_form_street3")
                city = left.text_input("Address 1: City", value=str(current.get("CITY") or ""), key="account_form_city")
                province = right.selectbox("Address 1: State/Province", PROVINCES, index=option_index(list(PROVINCES), current.get("PROVINCE") or "NS"), key="account_form_province")
                postal_code = right.text_input("Address 1: ZIP/Postal Code", value=str(current.get("POSTAL_CODE") or ""), key="account_form_postal")
                country = right.text_input("Address 1: Country/Region", value=str(current.get("COUNTRY_REGION") or "Canada"), key="account_form_country")
                latitude = right.number_input("Address 1: Latitude", min_value=-90.0, max_value=90.0, value=float(current.get("LATITUDE") or 0.0), format="%.7f", key="account_form_latitude")
                longitude = right.number_input("Address 1: Longitude", min_value=-180.0, max_value=180.0, value=float(current.get("LONGITUDE") or 0.0), format="%.7f", key="account_form_longitude")
        with roles_tab:
            with st.container(border=True):
                role_values = {}
                columns = st.columns(3)
                for index, (field, label) in enumerate(ROLE_FIELDS):
                    role_values[field] = columns[index % 3].checkbox(label, value=bool(current.get(field)), key=f"account_form_role_{field.lower()}")

        if action == "save":
            errors = []
            if not account_name.strip():
                errors.append("Account Name is required.")
            if registration.strip():
                duplicates = repo.find_accounts_by_registration_number(registration.strip())
                if view.record_id:
                    duplicates = duplicates[duplicates["ACCOUNT_ID"] != view.record_id]
                if not duplicates.empty:
                    errors.append("Registration Number is already used by another Account.")
            if errors:
                for error in errors:
                    st.error(error)
            else:
                record = {
                    "ACCOUNT_ID": view.record_id,
                    "ORGANIZATION_NAME": account_name.strip(),
                    "CONTACT_EMAIL": email.strip() or None,
                    "CONTACT_PHONE": phone.strip() or None,
                    "FAX": fax.strip() or None,
                    "WEBSITE": website.strip() or None,
                    "REGISTRATION_NUMBER": registration.strip() or None,
                    "PROVINCE_OF_REGISTRATION": province_registration,
                    "PARENT_ACCOUNT_ID": lookup_options[parent_label],
                    "GRADING_STATION_ACCOUNT_ID": lookup_options[grading_label],
                    "PULLET_GROWER_ACCOUNT_ID": lookup_options[pullet_label],
                    "SPENT_FOWL_PLANS": spent_fowl_plans.strip() or None,
                    "DEFAULT_ON_REPORTS": default_reports,
                    "NO_SVG": no_svg,
                    "STATUS": status,
                    "DESCRIPTION": description.strip() or None,
                    "ADDRESS_LINE1": street1.strip() or None,
                    "ADDRESS_LINE2": street2.strip() or None,
                    "ADDRESS_LINE3": street3.strip() or None,
                    "CITY": city.strip() or None,
                    "PROVINCE": province,
                    "POSTAL_CODE": postal_code.strip() or None,
                    "COUNTRY_REGION": country.strip() or None,
                    "LATITUDE": latitude if latitude else None,
                    "LONGITUDE": longitude if longitude else None,
                    **role_values,
                }
                if not view.record_id:
                    record.pop("ACCOUNT_ID")
                elif view.name == "edit":
                    record["EXPECTED_UPDATED_AT"] = st.session_state.get(expected_stamp_key)
                try:
                    saved_id = repo.upsert_account(record)
                    clear_widget_prefix("account_form_")
                    open_view("detail", saved_id)
                except (ValueError, RepositoryError) as exc:
                    show_data_error(exc)
