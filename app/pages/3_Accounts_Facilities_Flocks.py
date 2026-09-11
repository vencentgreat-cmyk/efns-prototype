# ============================================================
# EFNS Prototype — Accounts, Facilities, and Facility Details
# ============================================================
"""Account and facility workspace; flock writes live on the dedicated page."""

import streamlit as st

from app.ui import apply_theme, clear_widget_prefix, page_header, section_intro
from data.constants import ACCOUNT_STATUSES, FACILITY_STATUSES
from data.repositories import get_repository

apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

def choice_index(options, current):
    return options.index(current) if current in options else 0

page_header(
    "Accounts & Facilities",
    "Manage accounts, facilities, and facility details in focused work areas.",
    "ACCOUNT & FACILITY",
)
st.info("The entity names and relationships remain provisional pending Dataverse metadata.")

tab1, tab2 = st.tabs(["Accounts", "Facilities"])

# =====================================================================
# ACCOUNTS
# =====================================================================
with tab1:
    section_intro("Accounts / Producers", "Organizations, contacts, roles, and registration identifiers.")
    accounts = repo.get_accounts()

    if not accounts.empty:
        st.dataframe(
            accounts[[
                "ACCOUNT_ID", "REGISTRATION_NUMBER", "ORGANIZATION_NAME",
                "CITY", "PROVINCE", "CONTACT_NAME", "CONTACT_EMAIL",
                "PRODUCER_ROLE", "BREEDER_ROLE", "HATCHERY_ROLE", "GRADER_ROLE",
                "STATUS",
            ]],
            width="stretch",
            height=410,
            hide_index=True,
            column_config={
                "ACCOUNT_ID": "Account ID",
                "REGISTRATION_NUMBER": "Registration",
                "ORGANIZATION_NAME": "Organization",
                "CONTACT_NAME": "Contact",
                "CONTACT_EMAIL": "Email",
                "PRODUCER_ROLE": "Producer",
                "BREEDER_ROLE": "Breeder",
                "HATCHERY_ROLE": "Hatchery",
                "GRADER_ROLE": "Grader",
            },
        )
    else:
        st.info("No accounts in the database.")

    with st.expander("Add or update an account", expanded=False):
        account_records = {
            f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER}": row.ACCOUNT_ID
            for row in accounts.itertuples()
        }
        account_record_label = st.selectbox(
            "Record", ["Create new", *account_records], key="acc_record",
            on_change=clear_widget_prefix, args=("acc_", ("acc_record",)),
        )
        current_account = (
            repo.get_account(account_records[account_record_label])
            if account_record_label != "Create new"
            else {}
        )
        identity_col, contact_col = st.columns(2)
        with identity_col:
            st.text_input("Account ID", value=current_account.get("ACCOUNT_ID", "Assigned when saved"), disabled=True, key="acc_id")
            org_name = st.text_input("Organization Name", value=str(current_account.get("ORGANIZATION_NAME") or ""), key="acc_name")
            reg_num = st.text_input("Registration Number", value=str(current_account.get("REGISTRATION_NUMBER") or ""), key="acc_reg")
            city = st.text_input("City", value=str(current_account.get("CITY") or ""), key="acc_city")
            status = st.selectbox("Status", ACCOUNT_STATUSES, index=choice_index(ACCOUNT_STATUSES, current_account.get("STATUS")), key="acc_status")
        with contact_col:
            contact = st.text_input("Contact Name", value=str(current_account.get("CONTACT_NAME") or ""), key="acc_contact")
            contact_email = st.text_input("Contact Email", value=str(current_account.get("CONTACT_EMAIL") or ""), key="acc_email")
            st.markdown("**Operational roles**")
            is_producer = st.checkbox("Producer Role", value=bool(current_account.get("PRODUCER_ROLE", True)), key="acc_prod")
            is_breeder = st.checkbox("Breeder Role", value=bool(current_account.get("BREEDER_ROLE", False)), key="acc_breed")
            is_hatchery = st.checkbox("Hatchery Role", value=bool(current_account.get("HATCHERY_ROLE", False)), key="acc_hatch")
            is_grader = st.checkbox("Grader Role", value=bool(current_account.get("GRADER_ROLE", False)), key="acc_grad")

        action_label = "Update Account" if current_account else "Create Account"
        if st.button(action_label, key="acc_save", type="primary"):
            if not org_name:
                st.error("Organization name is required.")
            else:
                record = {
                    "ORGANIZATION_NAME": org_name,
                    "REGISTRATION_NUMBER": reg_num or None,
                    "CITY": city or None,
                    "PROVINCE": "NS",
                    "CONTACT_NAME": contact or None,
                    "CONTACT_EMAIL": contact_email or None,
                    "STATUS": status,
                    "PRODUCER_ROLE": is_producer,
                    "BREEDER_ROLE": is_breeder,
                    "HATCHERY_ROLE": is_hatchery,
                    "GRADER_ROLE": is_grader,
                }
                if current_account:
                    record["ACCOUNT_ID"] = current_account["ACCOUNT_ID"]
                aid = repo.upsert_account(record)
                st.success(f"Account saved: {aid}")
                st.rerun()

    if not accounts.empty:
        relationship_labels = {
            f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER}": row.ACCOUNT_ID
            for row in accounts.itertuples()
        }
        with st.expander("Account relationships", expanded=False):
            relationship_label = st.selectbox(
                "Account record",
                list(relationship_labels),
                key="account_relationship_record",
            )
            relationship_account_id = relationship_labels[relationship_label]
            facilities_tab, flocks_tab, quotas_tab, quota_tx_tab, tests_tab, production_tab = st.tabs(
                ["Facilities", "Flocks", "Quota Registrations", "Quota Transactions", "Salmonella Tests", "Matched Production"]
            )
            related_sets = (
                (facilities_tab, repo.get_facilities(account_id=relationship_account_id)),
                (flocks_tab, repo.get_flocks(account_id=relationship_account_id)),
                (quotas_tab, repo.get_quota_registrations(account_id=relationship_account_id)),
                (quota_tx_tab, repo.get_quota_transactions(account_id=relationship_account_id)),
                (tests_tab, repo.get_salmonella_tests(account_id=relationship_account_id)),
            )
            for related_tab, related_frame in related_sets:
                with related_tab:
                    if related_frame.empty:
                        st.info("No related records.")
                    else:
                        st.dataframe(related_frame, width="stretch", height=300, hide_index=True)
            with production_tab:
                production = repo.get_production_records()
                if "PRODUCER_ACCOUNT_ID" in production:
                    production = production[production["PRODUCER_ACCOUNT_ID"] == relationship_account_id]
                else:
                    production = production.iloc[0:0]
                if "MATCH_STATUS" in production:
                    production = production[production["MATCH_STATUS"].fillna("") != "UNMATCHED"]
                if production.empty:
                    st.info("No production records are successfully linked to this account.")
                else:
                    st.dataframe(production, width="stretch", height=300, hide_index=True)

# =====================================================================
# FACILITIES
# =====================================================================
with tab2:
    section_intro("Facilities", "Physical facilities associated with producer accounts.")
    facilities = repo.get_facilities()

    if not facilities.empty:
        # Merge with account names for readability
        acc = repo.get_accounts()
        df_show = facilities.merge(
            acc[["ACCOUNT_ID", "ORGANIZATION_NAME"]],
            on="ACCOUNT_ID",
            how="left",
        )
        st.dataframe(
            df_show[[
                "FACILITY_ID", "ORGANIZATION_NAME", "FACILITY_NAME",
                "FACILITY_TYPE", "STATUS", "ACTIVATION_DATE", "CLOSURE_DATE",
            ]],
            width="stretch",
            height=410,
            hide_index=True,
            column_config={
                "FACILITY_ID": "Facility ID",
                "ORGANIZATION_NAME": "Account",
                "FACILITY_NAME": "Facility",
                "FACILITY_TYPE": "Type",
                "ACTIVATION_DATE": "Activated",
                "CLOSURE_DATE": "Closed",
            },
        )
    else:
        st.info("No facilities in the database.")

    with st.expander("Add or update a facility", expanded=False):
        accounts_for_picker = repo.get_accounts()
        acc_options = {
            f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID
            for row in accounts_for_picker.itertuples()
        }
        facility_records = {
            f"{row.FACILITY_NAME} · {row.FACILITY_ID[:8]}": row.FACILITY_ID
            for row in facilities.itertuples()
        }
        facility_record_label = st.selectbox(
            "Record", ["Create new", *facility_records], key="fac_record",
            on_change=clear_widget_prefix, args=("fac_", ("fac_record",)),
        )
        current_facility = {}
        if facility_record_label != "Create new":
            facility_id = facility_records[facility_record_label]
            current_facility = facilities[facilities["FACILITY_ID"] == facility_id].iloc[0].to_dict()
        st.text_input("Facility ID", value=current_facility.get("FACILITY_ID", "Assigned when saved"), disabled=True, key="fac_id")
        fac_name = st.text_input("Facility Name", value=str(current_facility.get("FACILITY_NAME") or ""), key="fac_name")
        facility_types = ("Pullet", "Layer", "Other")
        fac_type = st.selectbox("Facility Type", facility_types, index=choice_index(facility_types, current_facility.get("FACILITY_TYPE")), key="fac_type")
        fac_status = st.selectbox("Facility Status", FACILITY_STATUSES, index=choice_index(FACILITY_STATUSES, current_facility.get("STATUS")), key="fac_status")
        account_labels = list(acc_options)
        account_index = next((index for index, label in enumerate(account_labels) if acc_options[label] == current_facility.get("ACCOUNT_ID")), 0)
        selected_acc = st.selectbox(
            "Account",
            account_labels,
            index=account_index,
            key="fac_account",
        )

        action_label = "Update Facility" if current_facility else "Create Facility"
        if st.button(action_label, key="fac_save", type="primary"):
            if not fac_name:
                st.error("Facility name and account are required.")
            else:
                record = {
                    "FACILITY_NAME": fac_name,
                    "FACILITY_TYPE": fac_type,
                    "STATUS": fac_status,
                    "ACCOUNT_ID": acc_options[selected_acc],
                }
                if current_facility:
                    record["FACILITY_ID"] = current_facility["FACILITY_ID"]
                fid = repo.upsert_facility(record)
                st.success(f"Facility saved: {fid}")
                st.rerun()

    if not facilities.empty:
        section_intro("Facility Details", "Provisional barn or house subdivisions linked by Facility ID.")
        facility_detail_labels = {
            f"{row.FACILITY_NAME} · {row.FACILITY_ID[:8]}": row.FACILITY_ID
            for row in facilities.itertuples()
        }
        detail_facility_label = st.selectbox(
            "Facility for details", list(facility_detail_labels), key="facility_detail_filter"
        )
        detail_facility_id = facility_detail_labels[detail_facility_label]
        facility_details = repo.get_facility_details(facility_id=detail_facility_id)
        if facility_details.empty:
            st.info("No facility details are linked to this facility.")
        else:
            st.dataframe(facility_details, width="stretch", height=260, hide_index=True)
        with st.expander("Add a Facility Detail", expanded=False):
            detail_name = st.text_input("Detail Name *", key="facility_detail_name")
            detail_type = st.text_input("Detail Type", value="Barn Area", key="facility_detail_type")
            detail_comments = st.text_area("Detail Comments", key="facility_detail_comments")
            if st.button("Save Facility Detail", type="primary", key="facility_detail_save"):
                if not detail_name.strip():
                    st.error("Detail Name is required.")
                else:
                    detail_id = repo.upsert_facility_detail(
                        {
                            "FACILITY_ID": detail_facility_id,
                            "DETAIL_NAME": detail_name.strip(),
                            "DETAIL_TYPE": detail_type or None,
                            "STATUS": "Active",
                            "COMMENTS": detail_comments or None,
                        }
                    )
                    st.success(f"Facility Detail saved: {detail_id}")
                    st.rerun()
