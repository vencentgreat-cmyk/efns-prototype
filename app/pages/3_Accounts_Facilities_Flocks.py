# ============================================================
# EFNS Prototype v0.1 — Accounts, Facilities, Flocks Page
# ============================================================
"""CRUD-style prototype views. All schema is PROVISIONAL."""

import uuid

import pandas as pd
import streamlit as st

from data.repositories import get_repository


st.set_page_config(page_title="Accounts / Facilities / Flocks", page_icon="🥚")

if "repo" not in st.session_state:
    st.session_state.repo = get_repository()

repo = st.session_state.repo

st.title("Accounts, Facilities & Flocks")
st.caption("Operational entity views — **PROVISIONAL SCHEMA** (pending Dataverse inspection)")

st.warning(
    "Tables, fields, and relationships below are provisional and will change "
    "after the existing EIMS Dataverse metadata is obtained."
)

tab1, tab2, tab3 = st.tabs(["Accounts", "Facilities", "Flocks"])

# =====================================================================
# ACCOUNTS
# =====================================================================
with tab1:
    st.subheader("Accounts / Producers")
    accounts = repo.get_accounts()

    # Side-by-side: table + edit/create
    view_col, edit_col = st.columns([2, 1])

    with view_col:
        if not accounts.empty:
            st.dataframe(
                accounts[[
                    "ACCOUNT_ID", "REGISTRATION_NUMBER", "ORGANIZATION_NAME",
                    "CITY", "PROVINCE", "CONTACT_NAME", "CONTACT_EMAIL",
                    "PRODUCER_ROLE", "BREEDER_ROLE", "HATCHERY_ROLE", "GRADER_ROLE",
                    "STATUS",
                ]],
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No accounts in the database.")

    with edit_col:
        st.markdown("#### Add / Edit Account")
        existing_id = st.text_input("Account ID (leave blank to create new)", key="acc_id")
        org_name = st.text_input("Organization Name", key="acc_name")
        reg_num = st.text_input("Registration Number", key="acc_reg")
        city = st.text_input("City", key="acc_city")
        contact = st.text_input("Contact Name", key="acc_contact")
        contact_email = st.text_input("Contact Email", key="acc_email")
        status = st.selectbox("Status", ["Active", "Inactive"], key="acc_status")

        is_producer = st.checkbox("Producer Role", value=True, key="acc_prod")
        is_breeder = st.checkbox("Breeder Role", key="acc_breed")
        is_hatchery = st.checkbox("Hatchery Role", key="acc_hatch")
        is_grader = st.checkbox("Grader Role", key="acc_grad")

        if st.button("Save Account", key="acc_save"):
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

# =====================================================================
# FACILITIES
# =====================================================================
with tab2:
    st.subheader("Facilities")
    facilities = repo.get_facilities()

    view_col2, edit_col2 = st.columns([2, 1])

    with view_col2:
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
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.info("No facilities in the database.")

    with edit_col2:
        st.markdown("#### Add / Edit Facility")
        existing_fid = st.text_input("Facility ID (leave blank to create new)", key="fac_id")
        fac_name = st.text_input("Facility Name", key="fac_name")
        fac_type = st.selectbox("Facility Type", ["Pullet", "Layer", "Other"], key="fac_type")
        fac_status = st.selectbox("Facility Status", ["Active", "Inactive", "Closed"], key="fac_status")
        # Pick account
        accounts_for_picker = repo.get_accounts()
        acc_options = dict(
            zip(accounts_for_picker["ORGANIZATION_NAME"], accounts_for_picker["ACCOUNT_ID"])
        )
        selected_acc = st.selectbox(
            "Account",
            ["-- Select --"] + list(acc_options.keys()),
            key="fac_account",
        )

        if st.button("Save Facility", key="fac_save"):
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

# =====================================================================
# FLOCKS
# =====================================================================
with tab3:
    st.subheader("Flocks")
    # Filter
    all_accounts = repo.get_accounts()
    acc_map = dict(zip(all_accounts["ORGANIZATION_NAME"], all_accounts["ACCOUNT_ID"]))
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
        st.dataframe(
            df_show[[
                "FLOCK_ID", "FLOCK_NUMBER", "ORGANIZATION_NAME", "FACILITY_NAME",
                "BIRD_COUNT", "PLACEMENT_DATE", "HATCH_DATE", "EGG_COLOUR",
                "EST_PROD_COMPLETION", "EST_DISPOSAL", "ACTUAL_DISPOSAL",
                "DISPOSAL_METHOD", "STATUS",
            ]],
            use_container_width=True,
            hide_index=True,
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
                    use_container_width=True,
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