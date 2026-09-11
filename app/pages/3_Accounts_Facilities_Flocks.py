# ============================================================
# EFNS Prototype v0.1 — Accounts, Facilities, Flocks Page
# ============================================================
"""CRUD-style prototype views. All schema is PROVISIONAL."""

import streamlit as st

from app.ui import apply_theme, page_header, section_intro
from data.repositories import get_repository

apply_theme()
if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

page_header(
    "Accounts, Facilities & Flocks",
    "Manage the provisional operational hierarchy in clear, focused work areas.",
    "ACCOUNT & FACILITY",
)
st.info("The entity names and relationships remain provisional pending Dataverse metadata.")

tab1, tab2, tab3 = st.tabs(["Accounts", "Facilities", "Flocks"])

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
        st.caption("Leave Account ID blank to create a record. Enter an existing ID to update it.")
        identity_col, contact_col = st.columns(2)
        with identity_col:
            existing_id = st.text_input("Account ID", key="acc_id")
            org_name = st.text_input("Organization Name", key="acc_name")
            reg_num = st.text_input("Registration Number", key="acc_reg")
            city = st.text_input("City", key="acc_city")
            status = st.selectbox("Status", ["Active", "Inactive"], key="acc_status")
        with contact_col:
            contact = st.text_input("Contact Name", key="acc_contact")
            contact_email = st.text_input("Contact Email", key="acc_email")
            st.markdown("**Operational roles**")
            is_producer = st.checkbox("Producer Role", value=True, key="acc_prod")
            is_breeder = st.checkbox("Breeder Role", key="acc_breed")
            is_hatchery = st.checkbox("Hatchery Role", key="acc_hatch")
            is_grader = st.checkbox("Grader Role", key="acc_grad")

        action_label = "Update Account" if existing_id.strip() else "Create Account"
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
                if existing_id.strip():
                    record["ACCOUNT_ID"] = existing_id.strip()
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
        st.caption("Leave Facility ID blank to create a record. Enter an existing ID to update it.")
        existing_fid = st.text_input("Facility ID (leave blank to create new)", key="fac_id")
        fac_name = st.text_input("Facility Name", key="fac_name")
        fac_type = st.selectbox("Facility Type", ["Pullet", "Layer", "Other"], key="fac_type")
        fac_status = st.selectbox("Facility Status", ["Active", "Inactive", "Closed"], key="fac_status")
        # Pick account
        accounts_for_picker = repo.get_accounts()
        acc_options = {
            f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID
            for row in accounts_for_picker.itertuples()
        }
        selected_acc = st.selectbox(
            "Account",
            ["-- Select --"] + list(acc_options.keys()),
            key="fac_account",
        )

        action_label = "Update Facility" if existing_fid.strip() else "Create Facility"
        if st.button(action_label, key="fac_save", type="primary"):
            if not fac_name or selected_acc == "-- Select --":
                st.error("Facility name and account are required.")
            else:
                record = {
                    "FACILITY_NAME": fac_name,
                    "FACILITY_TYPE": fac_type,
                    "STATUS": fac_status,
                    "ACCOUNT_ID": acc_options[selected_acc],
                }
                if existing_fid.strip():
                    record["FACILITY_ID"] = existing_fid.strip()
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

# =====================================================================
# FLOCKS
# =====================================================================
with tab3:
    section_intro("Flocks", "Placement, status, facility assignment, and transaction history.")
    # Filter
    all_accounts = repo.get_accounts()
    acc_map = {
        f"{row.ORGANIZATION_NAME} · {row.REGISTRATION_NUMBER or row.ACCOUNT_ID[:8]}": row.ACCOUNT_ID
        for row in all_accounts.itertuples()
    }
    filter_acc = st.selectbox(
        "Filter by Account",
        ["All"] + list(acc_map.keys()),
        key="flock_filter",
    )
    aid = acc_map.get(filter_acc) if filter_acc != "All" else None

    flocks = repo.get_flocks(account_id=aid)

    if not flocks.empty:
        # Merge for readability
        acc_df = all_accounts[["ACCOUNT_ID", "ORGANIZATION_NAME"]]
        fac_df = repo.get_facilities()[["FACILITY_ID", "FACILITY_NAME"]]
        df_show = flocks.merge(acc_df, on="ACCOUNT_ID", how="left")
        df_show = df_show.merge(fac_df, on="FACILITY_ID", how="left", suffixes=("", "_FAC"))
        df_show["FACILITY_NAME"] = df_show["FACILITY_NAME"].fillna("Unassigned")
        st.dataframe(
            df_show[[
                "FLOCK_ID", "FLOCK_NUMBER", "ORGANIZATION_NAME", "FACILITY_NAME",
                "BIRD_COUNT", "PLACEMENT_DATE", "HATCH_DATE", "EGG_COLOUR",
                "EST_PROD_COMPLETION", "EST_DISPOSAL", "ACTUAL_DISPOSAL",
                "DISPOSAL_METHOD", "STATUS",
            ]],
            width="stretch",
            height=430,
            hide_index=True,
            column_config={
                "FLOCK_ID": "Flock ID",
                "FLOCK_NUMBER": "Flock",
                "ORGANIZATION_NAME": "Account",
                "FACILITY_NAME": "Facility",
                "BIRD_COUNT": st.column_config.NumberColumn("Bird Count", format="%d"),
                "PLACEMENT_DATE": "Placement",
                "HATCH_DATE": "Hatch Date",
                "EGG_COLOUR": "Egg Colour",
                "EST_PROD_COMPLETION": "Est. Completion",
                "EST_DISPOSAL": "Est. Disposal",
                "ACTUAL_DISPOSAL": "Actual Disposal",
                "DISPOSAL_METHOD": "Disposal Method",
            },
        )

        # Show transactions for selected flock
        st.divider()
        st.markdown("#### Flock Transactions")
        selected_flock = st.selectbox(
            "Select a flock to view transactions",
            df_show["FLOCK_NUMBER"].tolist(),
            key="tx_flock",
        )
        if selected_flock:
            flock_id = df_show[df_show["FLOCK_NUMBER"] == selected_flock]["FLOCK_ID"].iloc[0]
            txns = repo.get_flock_transactions(flock_id=flock_id)
            if not txns.empty:
                st.dataframe(
                    txns[["FLOCK_TRANSACTION_ID", "TRANSACTION_TYPE", "QUANTITY",
                           "TRANSACTION_DATE", "NOTES"]],
                    width="stretch",
                    hide_index=True,
                )
            else:
                st.info("No transactions for this flock.")
    else:
        st.info("No flocks found for the selected filter.")

    # Add flock form
    with st.expander("Add New Flock"):
        st.markdown("##### Add Flock")
        f_acc = st.selectbox("Account", ["-- Select --"] + list(acc_map.keys()), key="add_flock_acc")
        flock_num = st.text_input("Flock Number", key="add_flock_num")
        bird_ct = st.number_input("Bird Count", min_value=0, value=10000, key="add_flock_birds")
        egg_col = st.selectbox("Egg Colour", ["White", "Brown", "Mostly White", "Mostly Brown"], key="add_flock_colour")
        flock_stat = st.selectbox("Status", ["Planned", "Active", "Depopulated"], key="add_flock_status")

        if st.button("Add Flock", key="add_flock_btn"):
            if f_acc == "-- Select --" or not flock_num:
                st.error("Account and flock number are required.")
            else:
                record = {
                    "ACCOUNT_ID": acc_map[f_acc],
                    "FLOCK_NUMBER": flock_num,
                    "BIRD_COUNT": bird_ct,
                    "EGG_COLOUR": egg_col,
                    "STATUS": flock_stat,
                }
                fid = repo.upsert_flock(record)
                st.success(f"Flock created: {fid}")
                st.rerun()
