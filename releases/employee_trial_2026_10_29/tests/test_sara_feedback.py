"""Staff feedback regressions with local synthetic data only."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.entry_fields import bird_strain_options, quota_owner_errors
from app.services.production_data_display import production_display_records, production_detail_range
from app.services.production_reports import COMPONENTS, NEST_FIELDS
from app.services.export import spreadsheet_safe
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain
from tests.test_daily_quota_entry import quota_app

ROOT = Path(__file__).resolve().parents[1]


def entry_app(repo, tmp_path, monkeypatch, page, view='new', identity=None):
    app = authenticated_app(ROOT/'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repo
    app.session_state[f'_efns_record_{page}_view'] = view
    if identity:
        app.session_state[f'_efns_record_{page}_id'] = identity
    return app.switch_page(f'app/pages/{page}.py').run()


def test_registration_change_updates_owner_and_save(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,_=chain
    second=repo.upsert_quota_registration(dict(ACCOUNT_ID=other,QUOTA_NAME='Second register',
        REGISTRATION_NUMBER='Second',QUOTA_TYPE='Egg Production',STATUS='Active',EFFECTIVE_DATE='2020-01-01'))
    app=quota_app(repo,tmp_path,monkeypatch)
    assert not app.exception
    owner=lambda: next(m.value for m in app.markdown if '**Owner Account (from Quota Registration)**' in m.value)
    assert 'staff producer' in owner()
    option=next(value for value in app.selectbox(key='quota_tx_form_quota').options if 'Second register' in value)
    app.selectbox(key='quota_tx_form_quota').select(option).run()
    assert 'counterparty' in owner() and not any(w.label=='Owner Account' for w in app.text_input)
    app.selectbox(key='quota_tx_form_type').select('Adjustment').run()
    app.number_input(key='quota_tx_form_count').set_value(3)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    saved=repo.get_quota_transactions().iloc[0]
    assert saved.QUOTA_ID==second and saved.OWNER_ACCOUNT_ID==other
    # Editing and changing the registration also updates the owner before save.
    app.button(key='quota_tx_record_edit').click().run()
    option=next(value for value in app.selectbox(key='quota_tx_form_quota').options if 'DEV_TEST register' in value)
    app.selectbox(key='quota_tx_form_quota').select(option).run()
    assert 'staff producer' in owner()
    app.text_input(key='quota_tx_form_revision_reason').input('Synthetic owner follow-up')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_quota_transaction(saved.QUOTA_TRANSACTION_ID)['OWNER_ACCOUNT_ID']==account


def test_stale_owner_is_rejected_before_save(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,_=chain
    original=repo.get_quota_registration
    monkeypatch.setattr(repo,'get_quota_registration',lambda identity: dict(original(identity),ACCOUNT_ID=other))
    app=quota_app(repo,tmp_path,monkeypatch)
    app.selectbox(key='quota_tx_form_type').select('Adjustment').run()
    app.number_input(key='quota_tx_form_count').set_value(3)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception
    assert any('Owner Account does not match' in e.value for e in app.error)
    assert repo.get_quota_transactions().empty
    assert quota_owner_errors({'ACCOUNT_ID':account},{'OWNER_ACCOUNT_ID':other})
    assert not quota_owner_errors({'ACCOUNT_ID':account},{'OWNER_ACCOUNT_ID':account})
    assert quota_owner_errors(None,{'OWNER_ACCOUNT_ID':account})


def test_bird_strain_list_exact_values_and_current():
    frame=pd.DataFrame({'BIRD_STRAIN':['Hy-Line','Lohmann','Hy-Line',None,'  ','Novogen']})
    assert bird_strain_options(frame,'Legacy breed',constants=('Constant breed',))==[
        '', 'Constant breed','Hy-Line','Legacy breed','Lohmann','Novogen','Other']
    assert bird_strain_options(pd.DataFrame())==['','Other']
    assert ' Exact spelling ' in bird_strain_options(frame,' Exact spelling ')


def test_flock_dropdown_other_and_preserve_existing(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,_=chain
    repo._flocks.loc[repo._flocks.FLOCK_ID.eq(flock),'BIRD_STRAIN']='Legacy breed not in constants'
    extra=repo._flocks.iloc[0].copy();extra['FLOCK_ID']='known-strain-fixture';extra['BIRD_STRAIN']='Lohmann'
    repo._flocks=pd.concat([repo._flocks,pd.DataFrame([extra])],ignore_index=True)
    app=entry_app(repo,tmp_path,monkeypatch,'5_Flocks','edit',flock)
    assert not app.exception
    assert app.selectbox(key='flock_form_strain').value=='Legacy breed not in constants'
    app.selectbox(key='flock_form_strain').select('Lohmann').run()
    assert app.selectbox(key='flock_form_strain').value=='Lohmann'
    app.selectbox(key='flock_form_strain').select('Other').run()
    assert any(w.key=='flock_form_strain_other' for w in app.text_input)
    app.text_input(key='flock_form_strain_other').input('Exact new breed')
    app.text_input(key='flock_form_revision_reason').input('Synthetic breed entry')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_flock(flock)['BIRD_STRAIN']=='Exact new breed'
    app.button(key='flock_record_edit').click().run()
    assert app.selectbox(key='flock_form_strain').value=='Exact new breed'
    assert not any(w.key=='flock_form_strain_other' for w in app.text_input)
    # Save a different field without altering the previously unknown strain.
    app.text_area(key='flock_form_comments').input('Synthetic comment only')
    app.text_input(key='flock_form_revision_reason').input('Synthetic preserve breed')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_flock(flock)['BIRD_STRAIN']=='Exact new breed'


def test_salmonella_permit_is_derived_confirmation(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,_=chain
    app=entry_app(repo,tmp_path,monkeypatch,'9_Salmonella_Tests')
    assert not app.exception
    assert app.selectbox(key='salmonella_form_flock')
    assert any('Selected flock permit (read-only): DEV_TEST permit' in c.value for c in app.caption)
    assert not any(w.label=='Permit Number' for w in app.text_input)


def production_sources():
    account='00000000-0000-0000-0000-000000000001'
    grader='00000000-0000-0000-0000-000000000002'
    accounts=pd.DataFrame([dict(ACCOUNT_ID=account,ORGANIZATION_NAME='Synthetic Producer',REGISTRATION_NUMBER='07022'),
        dict(ACCOUNT_ID=grader,ORGANIZATION_NAME='Synthetic Grader',REGISTRATION_NUMBER=None)])
    rows=pd.DataFrame([dict(PRODUCTION_ID='p1',PRODUCER_ACCOUNT_ID=account,REPORTING_YEAR=2026,
        REPORTING_WEEK=2,TOTAL=Decimal('24945.0000')),dict(PRODUCTION_ID='p2',PRODUCER_NUMBER='unlinked',
        REPORTING_YEAR=2026,REPORTING_WEEK=2,IMPORT_ID='fixture',TOTAL=None)])
    detail=dict(PRODUCTION_ID='p1',GRADER_ACCOUNT_ID=grader,MARKETING_TYPE='Regulated',
        HOUSING_SYSTEM='Enriched',EGG_TYPE='Regular',GRADER_NAME='Fallback grader')
    detail.update({field:Decimal(i)+Decimal('.1250') for i,field in enumerate(dict.fromkeys([*COMPONENTS.values(),*NEST_FIELDS.values()]))})
    return rows,pd.DataFrame([detail]),accounts


def test_production_display_source_columns_identity_and_exports():
    records,details,accounts=production_sources()
    before=records.copy(deep=True)
    result=production_display_records(records,details,accounts)
    assert len(result)==2 and result.iloc[0].PRODUCER_IDENTITY_LABEL=='Synthetic Producer · 07022'
    assert result.iloc[0].PRODUCER_ACCOUNT_ID==accounts.iloc[0].ACCOUNT_ID
    assert result.iloc[1].PRODUCER_IDENTITY_LABEL=='Source Producer # unlinked [fixture]'
    for label,field in {**COMPONENTS,**NEST_FIELDS}.items():
        assert result.iloc[0][label]==details.iloc[0][field]  # Exact fractions, no report rounding.
    assert result.iloc[0].GRADING_STATION=='Synthetic Grader'
    assert result.iloc[0].HOUSING_SYSTEM=='Enriched' and result.iloc[0].MARKETING_TYPE=='Regulated'
    assert result.iloc[0].TOTAL==Decimal('24945.0000')
    assert pd.isna(result.iloc[1]['J'])
    pd.testing.assert_frame_equal(records,before)
    assert production_detail_range(records)==(202602,202602)
    export=spreadsheet_safe(result)
    csv=pd.read_csv(BytesIO(export.to_csv(index=False).encode()),keep_default_na=False)
    buffer=BytesIO()
    with pd.ExcelWriter(buffer,engine='openpyxl') as writer: export.to_excel(writer,index=False)
    xlsx=pd.read_excel(BytesIO(buffer.getvalue()))
    assert set(COMPONENTS)<=set(csv) and set(COMPONENTS)<=set(xlsx)
    assert csv.iloc[0].PRODUCER_IDENTITY_LABEL==xlsx.iloc[0].PRODUCER_IDENTITY_LABEL=='Synthetic Producer · 07022'
    assert Decimal(str(csv.iloc[0].J))==details.iloc[0].JUMBO
    assert Decimal(str(xlsx.iloc[0].J))==details.iloc[0].JUMBO


def test_production_empty_missing_account_and_null_grader():
    records,details,accounts=production_sources()
    empty=production_display_records(records.iloc[:0],details.iloc[:0],accounts.iloc[:0])
    assert empty.empty and set(COMPONENTS)<=set(empty)
    assert production_detail_range(empty) is None
    result=production_display_records(records,details,accounts.iloc[:0])
    assert result.iloc[0].PRODUCER_IDENTITY_LABEL=='Linked account (details unavailable)'
    assert result.iloc[0].GRADING_STATION=='Fallback grader'
    assert result.iloc[1].GRADING_STATION==''


def test_production_page_table_exports_match(chain,tmp_path,monkeypatch):
    repo,*_=chain
    records,details,accounts=production_sources()
    combined=records.merge(details,on='PRODUCTION_ID',how='left')
    repo._production=combined
    repo._accounts=accounts
    from app.services import export
    captured=[];safe=export.spreadsheet_safe
    def capture(frame):
        captured.append(frame.copy(deep=True));return safe(frame)
    monkeypatch.setattr(export,'spreadsheet_safe',capture)
    app=entry_app(repo,tmp_path,monkeypatch,'2_Production_Data',view='list')
    assert not app.exception
    table=app.dataframe[0].value
    assert set(COMPONENTS)<=set(table) and {'NR25','NR17','HOUSING_SYSTEM','MARKETING_TYPE','GRADING_STATION','PRODUCER_ACCOUNT_ID'}<=set(table)
    assert table.iloc[0].PRODUCER_IDENTITY_LABEL=='Synthetic Producer · 07022'
    assert len(captured)==2
    pd.testing.assert_frame_equal(table.fillna(''),captured[0].fillna(''))
    pd.testing.assert_frame_equal(table.fillna(''),captured[1].fillna(''))
    assert any('Full production reports (Summary, by Producer, Details, Details by Grader, Nest Run) are in Report Center.'==c.value for c in app.caption)


def test_production_page_empty(chain,tmp_path,monkeypatch):
    repo,*_=chain
    app=entry_app(repo,tmp_path,monkeypatch,'2_Production_Data',view='list')
    assert not app.exception
    assert app.dataframe[0].value.empty
    assert set(COMPONENTS)<=set(app.dataframe[0].value)
