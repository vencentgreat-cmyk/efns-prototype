"""Delivery smoke: actual Streamlit pages with synthetic Mock data, no network."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import pandas as pd
import pytest
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain
from tests.test_daily_quota_entry import quota_app

ROOT=Path(__file__).resolve().parents[1]


def workspace(repo,tmp_path,monkeypatch):
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    return app


@pytest.mark.parametrize('page',['3_Accounts_Facilities_Flocks.py','5_Flocks.py',
    '8_Quota_Transactions.py','4_Reports.py','21_Record_History.py'])
def test_main_pages_load(chain,tmp_path,monkeypatch,page):
    app=workspace(chain[0],tmp_path,monkeypatch)
    app.switch_page('app/pages/'+page).run()
    assert not app.exception and not app.error


def test_new_registration_has_exactly_three_types(chain,tmp_path,monkeypatch):
    app=workspace(chain[0],tmp_path,monkeypatch)
    app.session_state['_efns_record_7_Quota_Registrations_view']='new'
    app.switch_page('app/pages/7_Quota_Registrations.py').run()
    assert not app.exception and not app.error
    assert app.selectbox(key='quota_reg_form_type').options==[
        'Egg Production','Non Commercial Pullet Quota','Commercial Pullet Grower']


def test_purchase_blank_price_persists_and_reloads_blank(chain,tmp_path,monkeypatch):
    repo,*_=chain
    app=quota_app(repo,tmp_path,monkeypatch)
    app.selectbox(key='quota_tx_form_type').select('Purchase').run()
    label=next(s for s in app.selectbox(key='quota_tx_form_related_account').options if 'counterparty' in s)
    app.selectbox(key='quota_tx_form_related_account').select(label)
    app.number_input(key='quota_tx_form_count').set_value(2.125)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    row=repo.get_quota_transactions().iloc[0]
    assert pd.isna(row.PRICE) and row.QUOTA_COUNT==2.125
    app.run()
    app.button(key='quota_tx_record_edit').click().run()
    assert not app.exception and app.text_input(key='quota_tx_form_price').value==''
    assert len(repo.get_quota_transactions())==1


def test_missing_purchase_counterparty_blocks_all_writes(chain,tmp_path,monkeypatch):
    repo,*_=chain
    app=quota_app(repo,tmp_path,monkeypatch)
    app.selectbox(key='quota_tx_form_type').select('Purchase').run()
    app.number_input(key='quota_tx_form_count').set_value(2)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and any('Related Account is required' in e.value for e in app.error)
    assert repo.get_quota_transactions().empty and repo.get_record_revisions().empty


@pytest.mark.parametrize('scenario',['negative','zero','switch'])
def test_adjustment_signed_input_and_switch_safety(chain,tmp_path,monkeypatch,scenario):
    repo,*_=chain
    app=quota_app(repo,tmp_path,monkeypatch)
    app.number_input(key='quota_tx_form_count').set_value(0 if scenario=='zero' else -5)
    if scenario=='switch':
        app.run()
        app.selectbox(key='quota_tx_form_type').select('Purchase').run()
        label=next(s for s in app.selectbox(key='quota_tx_form_related_account').options if 'counterparty' in s)
        app.selectbox(key='quota_tx_form_related_account').select(label)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception
    rows=repo.get_quota_transactions()
    if scenario=='negative':
        assert not app.error and len(rows)==1 and rows.iloc[0].QUOTA_COUNT==-5
        assert rows.iloc[0].TRANSACTION_TYPE=='Adjustment'
    else:
        assert app.error and rows.empty and repo.get_record_revisions().empty


def test_historical_lease_notes_edit_preserves_stored_values(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,*_=chain
    row=dict(QUOTA_TRANSACTION_ID='DEV_TEST smoke legacy',QUOTA_ID=quota,OWNER_ACCOUNT_ID=account,
        RELATED_ACCOUNT_ID=other,TRANSACTION_TYPE='Lease (In)',QUOTA_COUNT=Decimal('12.1250'),
        QUOTA_LEASE_TYPE='Non One Time Credit',PRICE=None,EFFECTIVE_DATE='2010-01-01',
        END_DATE='2011-01-01',COMMENTS='old',UPDATED_AT='2026-01-01T00:00:00.123456789')
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame([row])],ignore_index=True)
    before=repo._quota_transactions.copy(deep=True)
    app=quota_app(repo,tmp_path,monkeypatch,'edit',row['QUOTA_TRANSACTION_ID'])
    assert not app.exception and not app.error
    assert app.selectbox(key='quota_tx_form_type').value=='Lease (In)'
    assert app.selectbox(key='quota_tx_form_lease').value=='Non One Time Credit'
    app.text_area(key='quota_tx_form_comments').input('DEV_TEST smoke notes')
    app.text_input(key='quota_tx_form_revision_reason').input('DEV_TEST notes-only review')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    keep=[c for c in before if c not in {'COMMENTS','UPDATED_AT'}]
    pd.testing.assert_frame_equal(repo._quota_transactions[keep],before[keep])
    assert len(repo.get_record_revisions())==1


def test_flock_shows_latest_observation_not_established_usage(chain,tmp_path,monkeypatch):
    from data.business_time import halifax_today
    repo,account,other,facility,quota,flock,*_=chain
    repo.upsert_flock_transaction(dict(FLOCK_ID=flock,TRANSACTION_TYPE='Count',QUANTITY=7,
        TRANSACTION_DATE=halifax_today(),COUNT_SOURCE_LABEL='Producer'))
    before=repo._flocks.copy(deep=True)
    app=workspace(repo,tmp_path,monkeypatch)
    app.session_state['_efns_record_5_Flocks_view']='detail'
    app.session_state['_efns_record_5_Flocks_id']=flock
    app.switch_page('app/pages/5_Flocks.py').run()
    assert not app.exception and not app.error
    assert any(m.label=='Usage percentage' and m.value=='Not established' for m in app.metric)
    assert any('Latest Count observation' in m.value and '7' in m.value for m in app.markdown)
    pd.testing.assert_frame_equal(repo._flocks,before)


def test_grouped_report_exports_exact_preview(chain,tmp_path,monkeypatch):
    from app.services import report_center
    repo,account,other,facility,quota,*_=chain
    rows=[dict(QUOTA_TRANSACTION_ID=f'DEV_TEST smoke {i}',QUOTA_ID=quota,
        OWNER_ACCOUNT_ID=account,TRANSACTION_TYPE=kind,QUOTA_COUNT=qty)
        for i,(kind,qty) in enumerate([('Global Adjustment',2.125),('Global Adjustment',-1.0),
            ('Terminate Quota',0),('Base',None),('Lease (In)',4.5)])]
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame(rows)],ignore_index=True)
    exported={}
    for key,method in [('csv','report_csv'),('xlsx','report_xlsx')]:
        original=getattr(report_center,method)
        def capture(user,frame,*args,_key=key,_original=original,**kwargs):
            result=_original(user,frame,*args,**kwargs)
            exported[_key]=result
            return result
        monkeypatch.setattr(report_center,method,capture)
    app=workspace(repo,tmp_path,monkeypatch)
    app.switch_page('app/pages/4_Reports.py').run()
    app.radio(key='report_center_section').set_value('Customize Report').run()
    app.selectbox(key='custom_report_dataset').select('Quota Transactions').run()
    app.multiselect(key='custom_report_columns').set_value(['Transaction Type','Quota Count']).run()
    app.multiselect(key='custom_report_group').set_value(['Transaction Type']).run()
    app.selectbox(key='custom_report_aggregate_field').select('Quota Count').run()
    app.selectbox(key='custom_report_aggregate').select('sum')
    next(b for b in app.button if b.label=='Run Report').click().run()
    assert not app.exception and not app.error
    preview=app.session_state.custom_report_result
    pd.testing.assert_frame_equal(app.dataframe[-1].value,preview)
    assert len(preview)==4
    totals=dict(zip(preview['Transaction Type'],preview['Quota Count']))
    assert totals['Global Adjustment']==1.125 and totals['Terminate Quota']==0 and pd.isna(totals['Base'])
    for result in [pd.read_csv(BytesIO(exported['csv'])),pd.read_excel(BytesIO(exported['xlsx']))]:
        pd.testing.assert_frame_equal(result,preview,check_dtype=False)
