"""EFNS internal Report Center with curated reports and safe customization."""

from __future__ import annotations

import datetime as dt
from data.business_time import halifax_today

import pandas as pd
import streamlit as st

from app.auth import can_current, get_auth_store, require_page_permission
from app.navigation import format_timestamp, page_file, timestamp_columns
from app.security import Permission
from app.services.report_center import (
    CUSTOM_DATASETS, build_custom_report, build_quota_summary, build_quota_summary_details, report_csv,
    report_definition, report_xlsx, visible_catalog, FLOCK_RECORD_COUNT, FLOCK_RECORD_COUNT_LABEL, transaction_type_options,
    quota_account_label,
)
from app.services.flock_current_report import build_flock_current_report
from app.services.quota_reports import (build_quota_transactions_report,
    build_quota_leases_report, build_quota_history_report)
from data.position_evidence import number as quota_number
from app.services.production_reports import (build_production_report, build_nest_run_report,
    production_grader_options, week_range, MARKETING_TYPES, AMOUNTS, NEST_FIELDS,
    PRODUCTION_CAPTION, production_rounding_summary, production_compact_caption, production_notes_frame)
from app.services.flock_age_report import build_flock_age_report, build_flock_age_quotas
from app.services.quota_state import get_inactive_quota_transaction_ids
from app.services.flock_reports import (
    build_flock_status_report, build_flocks_counted_report,
    build_flocks_needing_counts_report, build_flock_disposals_report,
    build_flock_salmonella_schedule, build_scheduled_flock_placements,
    build_flock_status_by_producer_report,
)
from data.quota_position import load_rules
from app.ui import apply_theme, page_header, section_intro, show_data_error
from data.constants import (
    ACCOUNT_STATUSES, FACILITY_DETAIL_STATUSES, FACILITY_STATUSES,
    FARM_LOCATION_STATUSES, FLOCK_STATUSES,
    QUOTA_STATUSES, QUOTA_TYPES,
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


def load_flock_report_quotas(accounts, as_of):
    registrations = repo.get_quota_registrations()
    transactions = repo.get_quota_transactions()
    inactive_ids = get_inactive_quota_transaction_ids(repo,
        transactions.get('QUOTA_TRANSACTION_ID', pd.Series(dtype=object)).tolist(), user=user)
    quotas, _count, reasons = build_flock_age_quotas(
        registrations, transactions, accounts, as_of, inactive_ids, load_rules())
    return quotas, sorted({reason for values in reasons.values() for reason in values})


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
        if definition.category == 'Production' and definition.handler.startswith('production_'):
            prefix = definition.handler
            parameters = st.columns(3)
            year = parameters[0].number_input('Year',min_value=1900,max_value=9999,value=halifax_today().year,step=1,key=prefix+'_year') if prefix == 'production_nest_run' else halifax_today().year
            start = parameters[1].text_input('Start Week',value=str(year)+'01',key=prefix+'_start')
            end = parameters[2].text_input('End Week',value=str(year)+'53',key=prefix+'_end')
            source_accounts = repo.get_accounts()
            types,selected_accounts,grader_key = list(MARKETING_TYPES),None,None
            if prefix == 'production_management_grader':
                st.selectbox('Unit of Measure',['Dozens'],key=prefix+'_unit')
                account_options = {str(row['ACCOUNT_ID']):quota_account_label(row) for row in source_accounts.to_dict('records')}
                selected_accounts = st.multiselect('Account',list(account_options),default=list(account_options),format_func=account_options.get,key=prefix+'_accounts')
                selected_type = st.selectbox('Marketing Type',list(MARKETING_TYPES),index=list(MARKETING_TYPES).index('Regulated'),key=prefix+'_marketing')
                types = [selected_type]
                try:
                    bounds = week_range(start,end)
                    selector_records = repo.get_production_report_records(*bounds)
                    options = production_grader_options(selector_records,source_accounts,*bounds)
                except ValueError as exc:
                    options = {}
                    st.info(str(exc))
                grader_key = st.selectbox('Grading Station',[None,*sorted(options,key=lambda key:(options[key],key))],format_func=lambda key:options.get(key,'Select a Grading Station'),key=prefix+'_grader')
                if grader_key is None:
                    st.info('Select a Grading Station to run this report.')
                    st.session_state.pop(prefix+'_result',None)
            elif prefix != 'production_nest_run':
                types = st.multiselect('Type',list(MARKETING_TYPES),default=list(MARKETING_TYPES),key=prefix+'_types')
            notes_caption = st.empty()
            if st.button('Run Report',type='primary',key='run_'+prefix,disabled=prefix=='production_management_grader' and grader_key is None):
                st.session_state.pop(prefix+'_result',None)
                try:
                    bounds = week_range(start,end)
                    source_records = repo.get_production_report_records(*bounds)
                    if prefix == 'production_nest_run':
                        result,metadata = build_nest_run_report(source_records,source_accounts,year,*bounds)
                    else:
                        layout = prefix.removeprefix('production_management_')
                        result,metadata = build_production_report(source_records,source_accounts,*bounds,types,layout=layout,account_ids=selected_accounts,grader_key=grader_key)
                    st.session_state[prefix+'_result'] = result
                    st.session_state[prefix+'_metadata'] = metadata
                except ValueError as exc:
                    show_data_error(exc)
            result = st.session_state.get(prefix+'_result')
            if isinstance(result,pd.DataFrame):
                metadata = st.session_state[prefix+'_metadata']
                for header in metadata['headers']: st.markdown(header)
                notes_caption.caption(production_compact_caption(metadata))
                rounding_summary = production_rounding_summary(metadata)
                if rounding_summary:
                    st.info(rounding_summary)
                    with st.expander('Rounding differences', expanded=False):
                        st.dataframe(pd.DataFrame(metadata['rounding_differences']), hide_index=True, width='stretch')
                if metadata.get('record_notes'):
                    with st.expander('Source notes', expanded=False):
                        st.text('\n'.join(metadata['record_notes']))
                if result.empty: st.info('No production records match the selected parameters.')
                else:
                    formats = {column:lambda value:'' if quota_number(value) is None else f'{quota_number(value):,}' for column in [*AMOUNTS,*NEST_FIELDS] if column in result}
                    st.dataframe(result.style.format(formats),hide_index=True,width='stretch')
                if can_current(Permission.EXPORT_REPORT):
                    st.download_button('Export CSV',report_csv(user,result),prefix+'.csv','text/csv',key=prefix+'_csv')
                    st.download_button('Export XLSX',report_xlsx(user,result,notes=production_notes_frame(metadata)),prefix+'.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=prefix+'_xlsx')
            else:
                notes_caption.caption(PRODUCTION_CAPTION)
        elif definition.handler in {'quota_transactions', 'quota_leases', 'quota_leases_by_end_date', 'quota_history'}:
            prefix = definition.handler
            source_accounts, source_registrations = repo.get_accounts(), repo.get_quota_registrations()
            parameters = st.columns(3)
            if prefix == 'quota_transactions':
                start = parameters[0].date_input('Start Date', value=halifax_today().replace(month=1,day=1), key=prefix+'_start')
                as_of = parameters[1].date_input('End Date', value=halifax_today(), key=prefix+'_end')
            else:
                as_of = parameters[0].date_input('As of Date', value=halifax_today(), key=prefix+'_date')
            selected_type = parameters[2].selectbox('Quota Type', QUOTA_TYPES, index=QUOTA_TYPES.index('Egg Production'), key=prefix+'_type')
            account_id, account_label = None, 'All Accounts'
            if prefix == 'quota_history':
                account_options = {'All Accounts':None, **{quota_account_label(row)+' · '+str(row['ACCOUNT_ID']):row['ACCOUNT_ID'] for row in source_accounts.to_dict('records')}}
                account_label = st.selectbox('Account', list(account_options), key=prefix+'_account')
                account_id = account_options[account_label]
                st.caption('Active owner transactions on Active Registrations; pre-Base and expired lease rows remain visible with zero Adjust. Stored rows are not split or merged.')
            else:
                st.caption('Active owner transactions on Active Registrations; registration dates do not limit listing. Related Account is the counterparty. Explicit DEV_TEST data is excluded.')
            if st.button('Run Report', type='primary', key='run_'+prefix):
                st.session_state.pop(prefix+'_result', None)
                try:
                    source_transactions = repo.get_quota_transactions()
                    inactive_ids = get_inactive_quota_transaction_ids(repo, source_transactions.get('QUOTA_TRANSACTION_ID',pd.Series(dtype=object)).tolist(), user=user)
                    args = (source_accounts, source_registrations, source_transactions, inactive_ids)
                    if prefix == 'quota_transactions':
                        result, metadata = build_quota_transactions_report(*args, start, as_of, selected_type)
                    elif prefix == 'quota_history':
                        result, metadata = build_quota_history_report(*args, as_of, selected_type, account_id, rules=load_rules())
                    else:
                        result, metadata = build_quota_leases_report(*args, as_of, selected_type, by_end_date=prefix == 'quota_leases_by_end_date')
                    st.session_state[prefix+'_result'] = result
                    st.session_state[prefix+'_metadata'] = metadata
                    st.session_state[prefix+'_applied_account'] = account_label
                except ValueError as exc:
                    show_data_error(exc)
            result = st.session_state.get(prefix+'_result')
            if isinstance(result,pd.DataFrame):
                metadata = st.session_state[prefix+'_metadata']
                st.markdown(metadata['header'])
                if prefix == 'quota_history':
                    st.caption('Account: '+st.session_state[prefix+'_applied_account'])
                for note in metadata['notes']:
                    st.caption(note)
                if result.empty:
                    st.info('No report rows are available for the selected parameters. Review any evidence notes above.')
                else:
                    formats = {column:lambda value: '' if quota_number(value) is None else f'{quota_number(value):,}' for column in ('Price','Bird Count','Quota Count Adjust','Running Balance','Current Quota') if column in result}
                    st.dataframe(result.style.format(formats), hide_index=True, width='stretch')
                if can_current(Permission.EXPORT_REPORT):
                    st.download_button('Export CSV',report_csv(user,result),prefix+'.csv','text/csv',key=prefix+'_csv')
                    st.download_button('Export XLSX',report_xlsx(user,result),prefix+'.xlsx','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',key=prefix+'_xlsx')
        elif definition.handler in {"quota_summary", "quota_summary_details"}:
            prefix = definition.handler
            accounts = repo.get_accounts()
            account_options = {"All Accounts": None, **{quota_account_label(row): row['ACCOUNT_ID'] for row in accounts.to_dict('records')}}
            params = st.columns(4)
            as_of = params[0].date_input("As of Date", value=halifax_today(), key=prefix+"_as_of")
            quota_type = params[1].selectbox("Quota Type", QUOTA_TYPES, key=prefix+"_type")
            account_label = params[2].selectbox("Account", list(account_options), key=prefix+"_account")
            status = params[3].selectbox("Status", ["Active", "Inactive", "Expired", "All"], key=prefix+"_status")
            st.caption("Status filters Quota Registrations; registration dates do not limit Account listing. Address and contact details come from Account. Calculations use Active owner transactions and Active Registrations at the as-of date; unavailable state evidence leaves amounts unknown.")
            if prefix == 'quota_summary':
                st.caption('Issuance is the confirmed owner quota position at the as-of date.')
            else:
                st.caption('Details shows gross Base, Adjustment, Purchase, Global Adjustment and Lease (In) totals. Sale, Lease (Out) and Terminate Quota are not shown or subtracted; these totals differ from net Issuance.')
            if st.button("Run Report", type="primary", icon=":material/play_arrow:", key="run_"+prefix):
                st.session_state.pop(prefix+'_result', None)
                try:
                    builder = build_quota_summary if prefix == 'quota_summary' else build_quota_summary_details
                    result, metrics = builder(repo, user=user, as_of_date=as_of, quota_type=quota_type, account_id=account_options[account_label], status=None if status == "All" else status)
                    st.session_state[prefix+'_result'] = result
                    st.session_state[prefix+'_metrics'] = metrics
                    st.session_state[prefix+'_execution'] = dt.datetime.now(dt.timezone.utc)
                    st.session_state[prefix+'_parameters'] = {
                        "as_of": as_of, "quota_type": quota_type,
                        "account": account_label, "status": status,
                    }
                    audit("RUN_REPORT", definition.report_id, {"row_count": len(result), "quota_type": quota_type})
                except Exception as exc: show_data_error(exc)
            result = st.session_state.get(prefix+"_result")
            metrics = st.session_state.get(prefix+"_metrics")
            if isinstance(result, pd.DataFrame):
                applied = st.session_state.get(prefix+"_parameters", {})
                st.markdown("## " + definition.name)
                st.caption(
                    f"Quota Type: {applied.get('quota_type', quota_type)} · "
                    f"As of: {applied.get('as_of', as_of)} · "
                    f"Account: {applied.get('account', account_label)} · "
                    f"Status: {applied.get('status', status)} · "
                    f"Executed: {format_timestamp(st.session_state.get(prefix+'_execution'))}"
                )
                if prefix == 'quota_summary':
                    st.metric("Producers with positive Issuance", metrics["producer_count"])
                st.metric("Total Issuance" if prefix == 'quota_summary' else "Gross quota total", 'Unknown' if metrics['total_issuance'] is None else f"{metrics['total_issuance']:,.2f}")
                for note in metrics['notes']:
                    st.caption(note)
                if metrics['notes']:
                    st.caption('Totals sum known amounts; Accounts with unavailable amounts are excluded from the total.')
                st.caption(f"{max(len(result)-1, 0):,} report row(s), plus Totals where applicable")
                if result.empty: st.info("No quota report rows match the selected parameters.")
                else: st.dataframe(result, width="stretch", hide_index=True)
                downloads(result, prefix+"_report", definition.report_id)
        elif definition.handler in {'flock_status', 'flock_status_producer', 'flocks_counted', 'flocks_needing_counts', 'flock_disposals', 'flock_salmonella_schedule', 'scheduled_flock_placements'}:
            handler = definition.handler
            source_flocks, source_accounts = repo.get_flocks(), repo.get_accounts()
            params = st.columns(3)
            if handler == 'scheduled_flock_placements':
                start = params[0].date_input('Scheduled Placements Date Start', value=halifax_today(), key=handler+'_start')
                as_of = params[1].date_input('Scheduled Placements End Date', value=halifax_today()+dt.timedelta(days=30), key=handler+'_end')
            elif handler in {'flocks_counted', 'flock_disposals'}:
                start_label = 'Flock Count Start Date' if handler == 'flocks_counted' else 'Flock Disposal Start Date'
                end_label = 'Flocks Counted End Date' if handler == 'flocks_counted' else 'Flock Disposal End Date'
                start = params[0].date_input(start_label, value=halifax_today().replace(day=1), key=handler+'_start')
                as_of = params[1].date_input(end_label, value=halifax_today(), key=handler+'_end')
            else:
                as_of = params[0].date_input('As of Date' if handler == 'flock_status' else 'Report Date', value=halifax_today(), key=handler+'_date')
            mortality = (st if handler == 'scheduled_flock_placements' else params[1]).text_input('Mortality (% per month)', value='0.4', key=handler+'_mortality') if handler in {'flock_status', 'flock_status_producer', 'flock_salmonella_schedule', 'scheduled_flock_placements'} else None
            kinds = {str(value).strip() for value in source_flocks.get('FLOCK_QUOTA_TYPE', pd.Series(dtype=object)).dropna() if str(value).strip()}
            if handler in {'flock_status', 'flock_status_producer', 'flocks_needing_counts', 'flock_salmonella_schedule'}:
                kinds.discard('Special Permit')
            options = ['Egg Production', 'All', *sorted(kinds - {'Egg Production', 'All'})]
            selected_type = params[2].selectbox('Quota Type', options, key=handler+'_type')
            account_id, account_label = None, ''
            if handler == 'flock_status_producer':
                account_labels = {str(row['ACCOUNT_ID']): f"{row.get('ORGANIZATION_NAME', '')} · {row.get('REGISTRATION_NUMBER', '')} · {row['ACCOUNT_ID']}" for row in source_accounts.to_dict('records')}
                account_id = st.selectbox('Account', [None, *sorted(account_labels, key=lambda identity: account_labels[identity].casefold())], format_func=lambda identity: account_labels.get(identity, 'Select an Account'), key=handler+'_account')
                account_label = account_labels.get(account_id, '')
                if account_id is None:
                    st.session_state.pop(handler+'_result', None)
                    st.info('Select an Account to run Flock Status Report by Producer.')
            from_age, to_age, count_type = 19, 299, 'All'
            if handler == 'flock_salmonella_schedule':
                extra = st.columns(2)
                from_age = extra[0].number_input('Flock Minimum Age', min_value=0, value=19, step=1, key=handler+'_from_age')
                to_age = extra[1].number_input('Flock Maximum Age', min_value=0, value=255, step=1, key=handler+'_to_age')
                st.caption('Uses Flock Age inclusion and inventory, including Delivery fallback. Unknown Inventory excluded; DEV_TEST follows the same inclusion rules.')
            elif handler == 'scheduled_flock_placements':
                st.caption('Inventory uses the latest of all recorded dated Deliveries, otherwise BIRD_COUNT. Mortality is unused. Conflicting Delivery quantities remain unknown. Totals sum known values. Quota is confirmed at the start date; disposal uses actual, otherwise estimated, at that date.')
            elif handler == 'flocks_needing_counts':
                extra = st.columns(3)
                from_age = extra[0].number_input('From Age', min_value=0, value=19, step=1, key=handler+'_from_age')
                to_age = extra[1].number_input('To Age', min_value=0, value=299, step=1, key=handler+'_to_age')
                count_type = extra[2].selectbox('Count Type', ['All', 'Board', 'Producer', 'EFC/CEMA'], key=handler+'_count_type')
                st.caption('Uses placed Flock Age inclusion; Delivery is not a Count. EFC/CEMA means labels other than Producer or Board, including blank labels.')
            elif handler == 'flock_disposals':
                st.caption('Disposal Age = whole weeks from Hatch Date to actual Disposal Date +19. The offset is derived from 30 legacy fixtures, not a business rule. Placed uses earliest Delivery quantity, otherwise BIRD_COUNT.')
            if handler in {'flock_status', 'flocks_counted', 'flock_disposals'}:
                st.caption('Quota uses confirmed Account Egg Production positions at the report/end date. Unavailable state evidence leaves quota unknown. Totals sum known values.')
            elif handler == 'flock_status_producer':
                st.caption('NFPMC Allocation is province-wide confirmed Egg Production quota. Issuance is the selected Account quota. Provincial Utilization divides Account inventory by province allocation; row Util. divides by Account quota. Unavailable evidence remains unknown.')
            if st.button('Run Report', type='primary', key='run_'+handler, disabled=handler == 'flock_status_producer' and account_id is None):
                st.session_state.pop(handler+'_result', None)
                try:
                    quotas, reasons = load_flock_report_quotas(source_accounts, start if handler == 'scheduled_flock_placements' else as_of) if handler not in {'flocks_needing_counts', 'flock_salmonella_schedule'} else ({}, [])
                    summary = None
                    if handler == 'flock_status_producer':
                        result, summary = build_flock_status_by_producer_report(source_flocks, repo.get_flock_transactions(), source_accounts, repo.get_facilities(), quotas, as_of, account_id, mortality, selected_type)
                    elif handler == 'flock_salmonella_schedule':
                        result = build_flock_salmonella_schedule(source_flocks, repo.get_flock_transactions(), source_accounts, repo.get_facilities(), as_of, mortality, selected_type, from_age, to_age)
                    elif handler == 'scheduled_flock_placements':
                        result = build_scheduled_flock_placements(source_flocks, repo.get_flock_transactions(), source_accounts, repo.get_facilities(), quotas, start, as_of, mortality, selected_type)
                    elif handler == 'flock_status':
                        result, summary = build_flock_status_report(source_flocks, repo.get_flock_transactions(), source_accounts, repo.get_facilities(), quotas, as_of, mortality, selected_type)
                    elif handler == 'flocks_counted':
                        result = build_flocks_counted_report(source_flocks, repo.get_flock_transactions(), source_accounts, quotas, start, as_of, selected_type)
                    elif handler == 'flocks_needing_counts':
                        result = build_flocks_needing_counts_report(source_flocks, repo.get_flock_transactions(), source_accounts, as_of, selected_type, from_age, to_age, count_type)
                    else:
                        result = build_flock_disposals_report(source_flocks, source_accounts, quotas, start, as_of, selected_type, transactions=repo.get_flock_transactions(transaction_type='Delivery'))
                        reasons = [*reasons, *result.attrs.get('notes', [])]
                    st.session_state[handler+'_result'] = result
                    st.session_state[handler+'_summary'] = summary
                    st.session_state[handler+'_reasons'] = reasons
                    applied = f'As of/end date: {as_of} · Quota Type: {selected_type}'
                    if handler in {'flocks_counted', 'flock_disposals', 'scheduled_flock_placements'}:
                        applied += f' · Start date: {start}'
                        if handler == 'scheduled_flock_placements':
                            applied += f' · Mortality: {mortality}% (unused)'
                    elif handler in {'flock_status', 'flock_status_producer'}:
                        applied += f' · Mortality: {mortality}% per month'
                        if handler == 'flock_status_producer':
                            applied += f' · Account: {account_label}'
                    elif handler == 'flock_salmonella_schedule':
                        applied += f' · Mortality: {mortality}% per month · Age: {from_age}–{to_age}'
                    else:
                        applied += f' · Age: {from_age}–{to_age} · Count Type: {count_type}'
                    st.session_state[handler+'_parameters'] = applied
                except ValueError as exc:
                    show_data_error(exc)
            result = st.session_state.get(handler+'_result')
            if isinstance(result, pd.DataFrame):
                st.caption(st.session_state[handler+'_parameters'])
                summary = st.session_state.get(handler+'_summary')
                if summary is not None:
                    for label in ('Inventory Birds', 'NFPMC Allocation', 'Provincial Utilization', 'Issuance for Province', 'Producers with Quota'):
                        st.metric(label, str(summary[label]) if summary[label] is not None else '—')
                    st.caption(summary['Notes'])
                for reason in st.session_state.get(handler+'_reasons', []):
                    st.caption(reason)
                if result.empty:
                    st.info('No scheduled placements in this range.' if handler == 'scheduled_flock_placements' else 'No flocks disposed in this range.' if handler == 'flock_disposals' else 'No records match the selected parameters.')
                else:
                    st.caption(f'{len(result):,} report row(s), including totals where applicable.')
                    st.dataframe(result, hide_index=True, width='stretch')
                if can_current(Permission.EXPORT_REPORT):
                    st.download_button('Export CSV', report_csv(user, result), handler+'_report.csv', 'text/csv', key=handler+'_csv')
                    st.download_button('Export XLSX', report_xlsx(user, result), handler+'_report.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key=handler+'_xlsx')
        elif definition.handler == 'flock_age':
            age_flocks = repo.get_flocks()
            age_accounts = repo.get_accounts()
            kinds = sorted({str(v).strip() for v in age_flocks.get('FLOCK_QUOTA_TYPE', pd.Series(dtype=object)).dropna() if str(v).strip() and str(v).strip() != 'Special Permit'})
            options = ['All', *kinds]
            params = st.columns(3)
            age_date = params[0].date_input('As of Date', value=halifax_today(), key='flock_age_date')
            age_mortality = params[1].text_input('Mortality (% per month)', value='0.4', key='flock_age_mortality')
            age_type = params[2].selectbox('Quota Type', options, index=options.index('Egg Production') if 'Egg Production' in options else 0, key='flock_age_type')
            st.caption('Special Permit excluded. Quota uses confirmed owner Egg Production positions; unavailable transaction-state evidence leaves allocation and utilization unknown. Flock inclusion remains provisional.')
            if st.button('Run Report', type='primary', key='run_flock_age'):
                st.session_state.pop('flock_age_result', None)
                try:
                    quotas, quota_reasons = load_flock_report_quotas(age_accounts, age_date)
                    result, summary = build_flock_age_report(age_flocks, repo.get_flock_transactions(), age_accounts, repo.get_facilities(), quotas, age_date, age_mortality, age_type)
                    st.session_state.flock_age_result = result
                    st.session_state.flock_age_summary = summary
                    st.session_state.flock_age_quota_reasons = quota_reasons
                    st.session_state.flock_age_parameters = f'As of: {age_date} · Mortality: {age_mortality}% · Quota Type: {age_type}'
                except ValueError as exc:
                    show_data_error(exc)
            result = st.session_state.get('flock_age_result')
            if isinstance(result, pd.DataFrame):
                st.caption(st.session_state.flock_age_parameters)
                summary = st.session_state.flock_age_summary
                for label in ('Inventory Birds', 'NFPMC Allocation', 'Provincial Utilization', 'Issuance for Province', 'Producers with Quota'):
                    st.metric(label, str(summary[label]) if summary[label] is not None else '—')
                st.caption(summary['Notes'])
                for reason in st.session_state.get('flock_age_quota_reasons', []):
                    st.caption(reason)
                st.dataframe(result, hide_index=True, width='stretch')
                if can_current(Permission.EXPORT_REPORT):
                    st.download_button('Export CSV', report_csv(user, result), 'flock_age_report.csv', 'text/csv', key='flock_age_csv')
                    st.download_button('Export XLSX', report_xlsx(user, result), 'flock_age_report.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='flock_age_xlsx')
        elif definition.handler in ('flock_current', 'flock_current_producer'):
            source_flocks = repo.get_flocks()
            prefix = 'flock_current_producer' if definition.handler == 'flock_current_producer' else 'flock_current'
            selected_account = None
            if definition.handler == 'flock_current_producer':
                producer_accounts = repo.get_accounts()
                account_labels = {str(r.ACCOUNT_ID): f'{r.ORGANIZATION_NAME} · {r.REGISTRATION_NUMBER} · {r.ACCOUNT_ID}' for r in producer_accounts.itertuples()}
                selected_account = st.selectbox('Account', list(account_labels), format_func=account_labels.get, key=prefix+'_account') if account_labels else None
                source_flocks = source_flocks.loc[source_flocks.ACCOUNT_ID.eq(selected_account)]
            kinds = sorted({str(value).strip() for value in source_flocks.get('FLOCK_QUOTA_TYPE', pd.Series(dtype=object)).dropna() if str(value).strip()})
            options = ['All', *kinds]
            params = st.columns(3)
            report_date = params[0].date_input('As of Date' if selected_account is not None else 'Report date', value=halifax_today(), key=prefix+'_date')
            mortality = params[1].text_input('Mortality (% per month)', value='0.4', key=prefix+'_mortality')
            selected_type = params[2].selectbox('Quota Type', options, index=options.index('Egg Production') if 'Egg Production' in options else 0, key=prefix+'_type')
            st.caption('Provisional inclusion: Active Flocks only, before actual disposal when present, otherwise estimated disposal. Egg Production includes Special Permit. Subtotals sum known values and disclose exclusions.')
            if st.button('Run Report', type='primary', key='run_'+prefix):
                st.session_state.pop(prefix+'_result', None)
                try:
                    result = build_flock_current_report(source_flocks, repo.get_flock_transactions(), repo.get_accounts(), report_date, mortality, selected_type)
                    st.session_state[prefix+'_result'] = result
                    st.session_state[prefix+'_parameters'] = f'Report date: {report_date} · Mortality: {mortality}% per month · Quota Type: {selected_type}' + (f' · Account: {account_labels[selected_account]}' if selected_account is not None else '')
                except ValueError as exc:
                    show_data_error(exc)
            result = st.session_state.get(prefix+'_result')
            if isinstance(result, pd.DataFrame):
                st.caption(st.session_state[prefix+'_parameters'])
                if result.empty:
                    st.info('No Flocks match the report parameters.')
                else:
                    st.dataframe(result, hide_index=True, width='stretch')
                if can_current(Permission.EXPORT_REPORT):
                    st.download_button('Export CSV', report_csv(user, result), prefix+'_report.csv', 'text/csv', key=prefix+'_csv')
                    st.download_button('Export XLSX', report_xlsx(user, result), prefix+'_report.xlsx', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key=prefix+'_xlsx')
        elif definition.handler == "salmonella_report":
            st.info("Use the registered Salmonella Test Report page for the existing filterable report.")
            if st.button("Open Salmonella Test Report", icon=":material/lab_profile:"):
                st.switch_page(page_file("10_Salmonella_Report.py"))
        elif definition.input_entity:
            template_record_selector(definition.input_entity)

elif section == "Customize Report":
    require_page_permission(Permission.USE_REPORT_BUILDER)
    dataset = st.selectbox("Dataset", list(CUSTOM_DATASETS), key="custom_report_dataset")
    if st.session_state.get('_custom_dataset_context')!=dataset:
        for key in list(st.session_state):
            if key.startswith('custom_filter_') or key in ('custom_report_columns','custom_report_group','custom_report_aggregate_field','custom_report_operation','custom_report_result'):
                st.session_state.pop(key,None)
        st.session_state['_custom_dataset_context']=dataset
    _method, _id, definitions = CUSTOM_DATASETS[dataset]
    labels = {field.label: field.source for field in definitions}
    default_columns = list(labels)[:5]
    if dataset in {"Flocks", "Flock Transactions", "Production Records"}:
        default_columns += ["Flock Account", "Facility Account", "Facility Name"]
        if dataset == "Production Records":
            default_columns += ["Producer Account", "Flock Facility ID", "Report Facility ID", "Facility Source", "Facility Reference Comparison"]
    selected_labels = st.multiselect("Output columns", list(labels), default=default_columns, key="custom_report_columns")
    selected_fields = [labels[label] for label in selected_labels]

    accounts = repo.get_accounts(); farm_locations = repo.get_farm_locations(); facilities = repo.get_facilities(); flocks = repo.get_flocks()
    account_options = {"All": None, **{f"{r.ORGANIZATION_NAME} · {str(r.ACCOUNT_ID)[:8]}": r.ACCOUNT_ID for r in accounts.itertuples()}}
    farm_location_options = {"All": None, **{f"{r.LOCATION_NAME} · {str(r.FARM_LOCATION_ID)[:8]}": r.FARM_LOCATION_ID for r in farm_locations.itertuples()}}
    facility_options = {"All": None, **{f"{r.FACILITY_NAME} · {str(r.FACILITY_ID)[:8]}": r.FACILITY_ID for r in facilities.itertuples()}}
    flock_options = {"All": None, **{f"{r.FLOCK_NUMBER} · {str(r.FLOCK_ID)[:8]}": r.FLOCK_ID for r in flocks.itertuples()}}
    filters = {}
    filter_cols = st.columns(4)
    account_label = "Producer Account" if dataset == "Production Records" else "Flock Account" if dataset in {"Flocks", "Flock Transactions"} else "Owner or Related Account" if dataset=="Quota Transactions" else "Account"
    filters["account_id"] = account_options[filter_cols[0].selectbox(account_label, list(account_options), key="custom_filter_account",disabled=dataset=="Accounts")]
    filters["facility_id"] = facility_options[filter_cols[1].selectbox("Facility", list(facility_options), key="custom_filter_facility",disabled=dataset not in {"Facility Details","Flocks","Flock Transactions","Salmonella Tests","Production Records"})]
    filters["flock_id"] = flock_options[filter_cols[2].selectbox("Flock", list(flock_options), key="custom_filter_flock",disabled=dataset not in {"Flocks","Flock Transactions","Salmonella Tests","Production Records"})]
    status_values = {"Accounts": ACCOUNT_STATUSES, "Farm Locations": FARM_LOCATION_STATUSES, "Facilities": FACILITY_STATUSES, "Facility Details": FACILITY_DETAIL_STATUSES, "Flocks": FLOCK_STATUSES, "Quota Registrations": QUOTA_STATUSES}.get(dataset, ())
    status = filter_cols[3].selectbox("Status", ["All", *status_values], disabled=not status_values, key="custom_filter_status")
    if status != "All": filters["statuses"] = (status,)
    if dataset in {"Flocks", "Flock Transactions", "Production Records"}:
        ownership = st.columns(2)
        facility_account = ownership[0].selectbox("Facility Account", list(account_options), key="custom_filter_facility_account")
        filters["facility_account_id"] = account_options[facility_account]
        if dataset == "Production Records":
            flock_account = ownership[1].selectbox("Flock Account", list(account_options), key="custom_filter_flock_account")
            filters["flock_account_id"] = account_options[flock_account]
    if dataset == "Production Records":
        from data.source_scope import SOURCE_SCOPES
        filters['source_scope'] = st.selectbox('Source scope', SOURCE_SCOPES, key='custom_filter_source_scope')
        periods = repo.get_production_records()
        period_columns = st.columns(2)
        years = sorted(pd.to_numeric(periods.get("REPORTING_YEAR", pd.Series(dtype=float)), errors="coerce").dropna().astype(int).unique())
        year = period_columns[0].selectbox("Reporting Year", ["All", *years], key="custom_filter_reporting_year")
        year_rows = periods if year == "All" else periods[periods["REPORTING_YEAR"] == year]
        weeks = sorted(pd.to_numeric(year_rows.get("REPORTING_WEEK", pd.Series(dtype=float)), errors="coerce").dropna().astype(int).unique())
        week = period_columns[1].selectbox("Reporting Week", ["All", *weeks], key="custom_filter_reporting_week")
        filters["reporting_year"] = None if year == "All" else int(year)
        filters["reporting_week"] = None if week == "All" else int(week)
    extra = st.columns(4)
    farm_location_label = extra[0].selectbox("Farm Location", list(farm_location_options), disabled=dataset != "Farm Locations", key="custom_filter_farm_location")
    filters["farm_location_id"] = farm_location_options[farm_location_label] if dataset == "Farm Locations" else None
    quota_value = extra[1].selectbox("Quota Type", ["All", *QUOTA_TYPES], key="custom_filter_quota",disabled=dataset not in {"Flocks","Quota Registrations","Quota Transactions"})
    filters["quota_type"] = None if quota_value == "All" else quota_value
    transaction_values = transaction_type_options(repo, dataset)
    if st.session_state.get('custom_filter_transaction') not in ('All', *transaction_values):
        st.session_state.pop('custom_filter_transaction', None)
    transaction_value = extra[2].selectbox("Transaction Type", ["All", *transaction_values], disabled=not transaction_values, key="custom_filter_transaction")
    filters["transaction_type"] = None if transaction_value == "All" else transaction_value
    use_dates = extra[3].checkbox("Use date range", disabled=dataset not in {"Flocks","Flock Transactions","Quota Transactions","Salmonella Tests"}, key="custom_filter_use_dates")
    date_range = st.date_input("Date range", value=(halifax_today() - dt.timedelta(days=365), halifax_today()), disabled=not use_dates or dataset == "Production Records", key="custom_filter_dates")
    if dataset != "Production Records" and use_dates and isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        filters["date_from"], filters["date_to"] = date_range
        if dataset == 'Flocks':
            flock_date_fields={'Hatch Date':'HATCH_DATE','Placement Date':'PLACEMENT_DATE','Estimated Disposal Date':'EST_DISPOSAL','Actual Disposal Date':'DISPOSAL_DATE'}
            selected_date=st.selectbox('Flock date field',list(flock_date_fields),key='custom_filter_flock_date_field')
            filters['date_field']=flock_date_fields[selected_date]

    group_labels = st.multiselect("Group by", selected_labels, key="custom_report_group")
    group_by = [labels[label] for label in group_labels]
    numeric = [field for field in definitions if field.source in selected_fields and field.aggregations]
    aggregation_options = ["None", *[field.label for field in numeric]]
    if dataset == "Flocks" and group_by:
        aggregation_options = [FLOCK_RECORD_COUNT_LABEL, *[field.label for field in numeric]]
    if st.session_state.get("custom_report_aggregate_field") not in aggregation_options:
        st.session_state.custom_report_aggregate_field = aggregation_options[0]
    aggregation_field = st.selectbox("Aggregation field", aggregation_options, key="custom_report_aggregate_field")
    count_records = aggregation_field == FLOCK_RECORD_COUNT_LABEL
    aggregations = {}
    if aggregation_field != "None" and not count_records:
        field = next(field for field in numeric if field.label == aggregation_field)
        aggregations[field.source] = st.selectbox("Aggregation", field.aggregations, key="custom_report_aggregate")
    sort_options = ["None", *group_labels, FLOCK_RECORD_COUNT_LABEL] if count_records else ["None", *selected_labels]
    if st.session_state.get("custom_report_sort") not in sort_options:
        st.session_state.custom_report_sort = "None"
    sort_label = st.selectbox("Sort by", sort_options, key="custom_report_sort")
    sort_field = FLOCK_RECORD_COUNT if sort_label == FLOCK_RECORD_COUNT_LABEL else labels.get(sort_label)
    ascending = st.radio("Sort direction", ["Ascending", "Descending"], horizontal=True, key="custom_report_direction") == "Ascending"
    run, reset = st.columns(2)
    if reset.button("Reset configuration", icon=":material/restart_alt:", width="stretch"):
        for key in [key for key in st.session_state if key.startswith("custom_")]: st.session_state.pop(key, None)
        st.session_state.pop("custom_report_result", None); st.rerun()
    if run.button("Run Report", type="primary", icon=":material/play_arrow:", width="stretch"):
        try:
            result = build_custom_report(repo, user=user, dataset=dataset, selected_fields=selected_fields, filters=filters, sort_by=sort_field, ascending=ascending, group_by=group_by, aggregations=aggregations, count_records=count_records)
            st.session_state.custom_report_result = result
            st.session_state.custom_report_configuration = {"dataset": dataset, "selected_fields": selected_fields, "filters": {key: value for key, value in filters.items() if value not in (None, "", ())}, "group_by": group_by, "aggregations": aggregations, "sort_by": sort_field, "ascending": ascending, "count_records": count_records}
            audit("RUN_REPORT", "custom-builder", {"dataset": dataset, "row_count": len(result)})
        except Exception as exc: show_data_error(exc)
    result = st.session_state.get("custom_report_result")
    if isinstance(result, pd.DataFrame):
        section_intro("Preview", f"{len(result):,} result row(s); exports contain this exact filtered result and column order.")
        if 'Source Total missing count' in result and result['Source Total missing count'].sum() > 0:
            st.warning('Source Total sums known values only. Missing values remain unknown; these counts do not establish that all observations were reported or that units are uniform.')
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
