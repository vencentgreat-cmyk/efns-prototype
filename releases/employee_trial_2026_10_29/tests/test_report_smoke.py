"""Catalog-complete offline builder smoke coverage; no Snowflake connection."""
from datetime import date,timedelta
import re

import pandas as pd
import pytest

from app.services.report_center import REPORT_CATALOG,build_quota_summary,build_quota_summary_details,build_custom_report
from app.services.production_reports import build_production_report,build_nest_run_report,production_grader_options
from app.services.quota_reports import build_quota_transactions_report,build_quota_leases_report,build_quota_history_report
from app.services.flock_current_report import build_flock_current_report
from app.services.flock_age_report import build_flock_age_report,build_flock_age_quotas
from app.services.flock_reports import (build_flock_status_report,build_flock_status_by_producer_report,
    build_flock_salmonella_schedule,build_scheduled_flock_placements,build_flocks_counted_report,
    build_flocks_needing_counts_report,build_flock_disposals_report)
from app.services.salmonella_reporting import build_salmonella_report
from data.repositories.mock import MockRepository
from data.business_time import halifax_today
from data.quota_position import load_rules
from tests.test_report_center import user

AVAILABLE=[report for report in REPORT_CATALOG if report.status=='Available']
CASES=('normal','empty','nulls','no_rows')


def smoke_repository(case):
    repo=MockRepository(seed=42)
    today=halifax_today()
    account=repo._accounts.iloc[0].to_dict()
    account.update(ACCOUNT_ID='producer',REGISTRATION_NUMBER='7001',ORGANIZATION_NAME='Trial Producer',STATUS='Active',PRODUCER_ROLE=True)
    grader=dict(account,ACCOUNT_ID='grader',REGISTRATION_NUMBER='7002',ORGANIZATION_NAME='Trial Grader',GRADER_ROLE=True)
    repo._accounts=pd.DataFrame([account,grader])
    facility=repo._facilities.iloc[0].to_dict()
    facility.update(FACILITY_ID='barn',ACCOUNT_ID='producer',FACILITY_NAME='Trial barn')
    repo._facilities=pd.DataFrame([facility])
    flock=repo._flocks.iloc[0].to_dict()
    flock.update(FLOCK_ID='flock',ACCOUNT_ID='producer',FACILITY_ID='barn',FLOCK_NUMBER='100',PERMIT_NUMBER='100',
        FLOCK_QUOTA_TYPE='Egg Production',STATUS='Active',HATCH_DATE=today-timedelta(weeks=30),
        PLACEMENT_DATE=today,EST_DISPOSAL=today+timedelta(days=365),DISPOSAL_DATE=None,BIRD_COUNT=100,BIRDS_DISPOSED=90)
    repo._flocks=pd.DataFrame([flock,dict(flock,FLOCK_ID='disposed',FLOCK_NUMBER='101',PERMIT_NUMBER='101',DISPOSAL_DATE=today)])
    repo._flock_transactions=pd.DataFrame([dict(FLOCK_TRANSACTION_ID='count',FLOCK_ID='flock',TRANSACTION_TYPE='Count',
        TRANSACTION_DATE=today,QUANTITY=100,COUNT_SOURCE_LABEL='Producer')])
    quota=repo._quota_registrations.iloc[0].to_dict()
    quota.update(QUOTA_ID='quota',ACCOUNT_ID='producer',REGISTRATION_NUMBER='7001',QUOTA_TYPE='Egg Production',STATUS='Active')
    repo._quota_registrations=pd.DataFrame([quota])
    repo._quota_transactions=pd.DataFrame([
        dict(QUOTA_TRANSACTION_ID='base',QUOTA_ID='quota',OWNER_ACCOUNT_ID='producer',RELATED_ACCOUNT_ID='grader',
            TRANSACTION_TYPE='Base',EFFECTIVE_DATE=today-timedelta(days=1),END_DATE=None,QUOTA_COUNT=100,PRICE=None),
        dict(QUOTA_TRANSACTION_ID='lease',QUOTA_ID='quota',OWNER_ACCOUNT_ID='producer',RELATED_ACCOUNT_ID='grader',
            TRANSACTION_TYPE='Lease (Out)',EFFECTIVE_DATE=today,END_DATE=today+timedelta(days=30),QUOTA_COUNT=2,PRICE=None)])
    test=repo._salmonella_tests.iloc[0].to_dict()
    test.update(SALMONELLA_TEST_ID='test',ACCOUNT_ID='producer',FLOCK_ID='flock',TESTING_DATE=today)
    repo._salmonella_tests=pd.DataFrame([test])
    from app.services.production_reports import COMPONENTS,NEST_FIELDS
    production=repo._production.iloc[0].to_dict()
    production.update(PRODUCTION_ID='production',PRODUCER_ACCOUNT_ID='producer',GRADER_ACCOUNT_ID='grader',
        GRADER_NAME='Trial Grader',GRADER_NUMBER='7002',PRODUCER_NUMBER='7001',IMPORT_ID=None,
        SOURCE_WEEK_CODE=today.year*100+1,REPORTING_YEAR=today.year,REPORTING_WEEK=1,
        MARKETING_TYPE='RE',TOTAL=16,SOURCE_TYPE='Historical')
    production.update({field:1 for field in COMPONENTS.values()})
    production.update({field:0 for field in NEST_FIELDS.values()})
    production['TOTAL']=sum(production[field] for field in COMPONENTS.values())
    repo._production=pd.DataFrame([production,dict(production,PRODUCTION_ID='production-lb',MARKETING_TYPE='LB')])
    repo._import_batches=[]
    if case=='empty':
        for key,value in list(vars(repo).items()):
            if isinstance(value,pd.DataFrame): setattr(repo,key,value.iloc[:0].copy())
    elif case=='nulls':
        for key,value in list(vars(repo).items()):
            if not isinstance(value,pd.DataFrame): continue
            frame=value.copy()
            for column in frame:
                if (column in {'REGISTRATION_NUMBER','ORGANIZATION_NAME','ADDRESS_LINE1','CITY','PROVINCE','POSTAL_CODE','CONTACT_PHONE','FAX',
                    'BIRD_COUNT','BIRDS_DISPOSED','QUOTA_COUNT','QUANTITY','NUMBER_OF_SAMPLES','PRICE','TOTAL'}
                    or column.endswith('_DATE') or column in COMPONENTS.values() or column in NEST_FIELDS.values()):
                    frame[column]=None
            setattr(repo,key,frame)
    return repo


def run_report(definition,repo,case):
    handler=definition.handler
    today=halifax_today()
    as_of=date(1900,1,1) if case=='no_rows' else today
    if case=='no_rows' and handler in {'flock_age','flock_status','flock_status_producer','flock_current',
        'flock_current_producer','flock_salmonella_schedule','flocks_needing_counts'}:
        as_of=date(2200,1,1)  # Both fixture flocks are disposed/estimated ended by then.
    start=as_of.replace(day=1)
    a,f,t=repo.get_accounts(),repo.get_flocks(),repo.get_flock_transactions()
    ids=a.ACCOUNT_ID.tolist()
    account=ids[0] if ids else None
    registrations,activity=repo.get_quota_registrations(),repo.get_quota_transactions()
    quotas,_count,_reasons=build_flock_age_quotas(registrations,activity,a,as_of,set(),load_rules())
    if handler in {'quota_summary','quota_summary_details'}:
        return (build_quota_summary if handler=='quota_summary' else build_quota_summary_details)(repo,user=user(),as_of_date=as_of,quota_type='Egg Production')
    if handler.startswith('production_'):
        first,last=(190001,190053) if case=='no_rows' else (today.year*100+1,today.year*100+53)
        records=repo.get_production_report_records(first,last)
        if handler=='production_nest_run':return build_nest_run_report(records,a,first//100,first,last)
        layout=handler.removeprefix('production_management_')
        options=production_grader_options(records,a,first,last)
        return build_production_report(records,a,first,last,layout=layout,grader_key=next(iter(options),'ACCOUNT:grader') if layout=='grader' else None)
    if handler=='quota_transactions':return build_quota_transactions_report(a,registrations,activity,set(),start,as_of)
    if handler in {'quota_leases','quota_leases_by_end_date'}:
        return build_quota_leases_report(a,registrations,activity,set(),date(2200,1,1) if case=='no_rows' else as_of,by_end_date=handler.endswith('by_end_date'))
    if handler=='quota_history':return build_quota_history_report(a,registrations,activity,set(),as_of,rules=load_rules())
    if handler in {'flock_status','flock_age','flock_status_producer'}:
        if handler=='flock_status_producer':return build_flock_status_by_producer_report(f,t,a,repo.get_facilities(),quotas,as_of,account)
        return (build_flock_status_report if handler=='flock_status' else build_flock_age_report)(f,t,a,repo.get_facilities(),quotas,as_of)
    if handler in {'flock_current','flock_current_producer'}:
        if handler.endswith('producer'):f=f.loc[f.ACCOUNT_ID.eq(account)]
        return build_flock_current_report(f,t,a,as_of)
    if handler=='flock_salmonella_schedule':return build_flock_salmonella_schedule(f,t,a,repo.get_facilities(),as_of)
    if handler=='scheduled_flock_placements':return build_scheduled_flock_placements(f,t,a,repo.get_facilities(),quotas,as_of,as_of+timedelta(days=30))
    if handler=='flocks_counted':return build_flocks_counted_report(f,t,a,quotas,start,as_of)
    if handler=='flocks_needing_counts':return build_flocks_needing_counts_report(f,t,a,as_of)
    if handler=='flock_disposals':return build_flock_disposals_report(f,a,quotas,start,as_of,transactions=t)
    if handler=='salmonella_report':return build_salmonella_report(repo,date_from=start if case=='no_rows' else None,date_to=as_of if case=='no_rows' else None)
    if handler=='custom':
        return build_custom_report(repo,user=user(),dataset='Accounts',selected_fields=['ACCOUNT_ID','ORGANIZATION_NAME','REGISTRATION_NUMBER','CITY','PROVINCE'],filters={'keyword':'no such record'} if case=='no_rows' else {})
    raise AssertionError('Missing catalog smoke runner: '+definition.report_id)


def rendered_strings(value):
    if isinstance(value,pd.DataFrame):
        for cell in value.to_numpy().flat:
            # Arrow nulls stay missing cells, not literal "None"/"nan" text.
            # Check actual text; stringifying missing scalars would invent a failure
            # and force changes to intentional nullable report calculations.
            if isinstance(cell,str):yield cell
            elif not pd.isna(cell):yield str(cell)
        yield from rendered_strings(value.attrs)
    elif isinstance(value,dict):
        for item in value.values():yield from rendered_strings(item)
    elif isinstance(value,(list,tuple)):
        for item in value:yield from rendered_strings(item)
    elif isinstance(value,str):yield value


@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('definition',AVAILABLE,ids=lambda report:report.report_id)
def test_every_available_report_smoke(definition,case):
    result=run_report(definition,smoke_repository(case),case)
    frame=result[0] if isinstance(result,tuple) else result
    assert isinstance(frame,pd.DataFrame)
    for value in rendered_strings(result):
        assert not re.search(r'(?<!\w)(?:None|nan|NaT|<NA>)(?!\w)',value), (definition.report_id,case,value)
    if case=='empty':assert frame.empty


@pytest.mark.parametrize('case',CASES)
@pytest.mark.parametrize('definition',AVAILABLE,ids=lambda report:report.report_id)
def test_every_available_report_page_smoke(definition,case,tmp_path,monkeypatch):
    from pathlib import Path
    from tests.auth_support import authenticated_app
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=smoke_repository(case)
    page='10_Salmonella_Report.py' if definition.handler=='salmonella_report' else '4_Reports.py'
    app.switch_page('app/pages/'+page).run()
    if definition.handler=='custom':
        app.radio(key='report_center_section').set_value('Customize Report').run()
        run=next(button for button in app.button if button.label in ('Run Report','Run report','Run Preview','Preview Report'))
        run.click().run()
    elif definition.handler!='salmonella_report':
        app.session_state['report_center_open_report']=definition.report_id
        app.run()
        prefix=definition.handler
        if prefix=='flock_status_producer' and case!='empty':
            app.selectbox(key=prefix+'_account').set_value('producer').run()
        if prefix=='production_management_grader':
            options=production_grader_options(app.session_state['_base_repo'].get_production_report_records(halifax_today().year*100+1,halifax_today().year*100+53),
                app.session_state['_base_repo'].get_accounts(),halifax_today().year*100+1,halifax_today().year*100+53)
            if options:app.selectbox(key=prefix+'_grader').set_value(next(iter(options))).run()
        if case=='no_rows':
            empty_date=date(2200,1,1) if prefix in {'flock_age','flock_status','flock_status_producer',
                'flock_current','flock_current_producer','flock_salmonella_schedule','flocks_needing_counts'} else date(1900,1,1)
            for widget in app.date_input:
                if widget.key in {prefix+'_start',prefix+'_end',prefix+'_date',prefix+'_as_of'}:
                    widget.set_value(empty_date)
            for widget in app.text_input:
                if widget.key in {prefix+'_start',prefix+'_end'}:widget.set_value('190001')
            if prefix=='production_nest_run':app.number_input(key=prefix+'_year').set_value(1900)
        run=app.button(key='run_'+prefix)
        if not run.disabled:run.click().run()
    elif case=='no_rows':
        app.date_input(key='sal_rpt_dates').set_value((date(1900,1,1),date(1900,1,2))).run()
    assert not app.exception and not app.error
    for frame in app.dataframe:
        for value in rendered_strings(frame.value):
            assert not re.search(r'(?<!\w)(?:None|nan|NaT|<NA>)(?!\w)',value),(definition.report_id,case,value)
    for item in [*app.caption,*app.info,*app.warning,*app.markdown]:
        assert not re.search(r'(?<!\w)(?:None|nan|NaT|<NA>)(?!\w)',item.value),(definition.report_id,case,item.value)
    for widget in app.selectbox:
        for label in widget.options:
            if widget.key in {'custom_report_aggregate_field','custom_report_sort'} and label=='None':
                continue  # Intentional no-aggregation/no-sort choice, not a missing cell/note.
            assert not re.search(r'(?<!\w)(?:None|nan|NaT|<NA>)(?!\w)',label),(definition.report_id,case,label)


@pytest.mark.parametrize('definition',[report for report in REPORT_CATALOG if report.status!='Available'],ids=lambda report:report.report_id)
@pytest.mark.parametrize('case',CASES)
def test_nontrial_entries_always_show_message(definition,case,tmp_path,monkeypatch):
    from pathlib import Path
    from tests.auth_support import authenticated_app
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=smoke_repository(case)
    app.switch_page('app/pages/4_Reports.py').run()
    assert definition.status=='Not included in this trial'
    app.button(key='open_report_'+definition.report_id).click().run()
    assert not app.exception and not app.error
    assert any('not included in this trial' in item.value.lower() for item in app.info)
    assert not any(button.label=='Run Report' for button in app.button)


def test_custom_report_card_explains_where_to_run(tmp_path,monkeypatch):
    from pathlib import Path
    from tests.auth_support import authenticated_app
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.switch_page('app/pages/4_Reports.py').run()
    app.button(key='open_report_custom-builder').click().run()
    assert not app.exception and not app.error
    assert any('Customize Report section' in item.value for item in app.info)


def test_trial_readiness_artifact_hashes():
    import hashlib
    import json
    from pathlib import Path
    root=Path(__file__).resolve().parents[1]
    manifest=json.loads((root/'DELIVERY_RUNTIME_DIFF_20261030.json').read_text(encoding='utf-8'))
    entries=manifest['trial_readiness_artifacts']
    assert {entry['path'] for entry in entries}=={
        'tests/test_report_smoke.py','docs/codex_reports/TRIAL_READINESS_STATIC_SCAN_20261109.md'}
    for entry in entries:
        raw=(root/entry['path']).read_bytes().replace(b'\r\n',b'\n')
        assert hashlib.sha256(raw).hexdigest()==entry['candidate_lf_sha256']
