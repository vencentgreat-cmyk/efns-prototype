"""Zero is a confirmed observation, not a fictitious removal or missing value."""
from datetime import date
from decimal import Decimal
from io import BytesIO
from pathlib import Path
import pandas as pd
import pytest

from app.services.quota_usage import account_usage_context
from app.services.report_center import build_custom_report, report_csv, report_xlsx
from data.repositories.base import RepositoryError
from data.validation import validate_flock_transaction
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain
from tests.test_account_usage_quantity import ACTOR
from tests.test_report_center import user


def payload(flock, quantity=0, kind='Count'):
    return dict(FLOCK_ID=flock,TRANSACTION_TYPE=kind,QUANTITY=quantity,TRANSACTION_DATE=date.today())


@pytest.mark.parametrize('unknown',[False,True])
def test_current_zero_sets_known_quantity_and_retry_is_exactly_once(chain,unknown):
    r,a,o,f,q,flock,record=chain
    if unknown: r._flocks.loc[r._flocks.FLOCK_ID==flock,'BIRD_COUNT']=None
    before=r._flocks.drop(columns=['BIRD_COUNT','UPDATED_AT']).copy(deep=True)
    version=r.get_flock(flock)['UPDATED_AT']
    first=r.record_current_flock_quantity(payload(flock),'zero-request',version,'Observed zero; synthetic evidence',confirmed=True,actor=ACTOR)
    assert r.get_flock(flock)['BIRD_COUNT']==0
    summary=account_usage_context(r,a)['summaries'][0]
    assert summary['known_bird_count']==0 and summary['missing_count']==0 and summary['current_occupancy']==0
    assert summary['usage_percent'] is None  # Company still has no real baseline.
    second=r.record_current_flock_quantity(payload(flock),'zero-request',version,'Observed zero; synthetic evidence',confirmed=True,actor=ACTOR)
    assert second==first
    assert len(r.get_flock_transactions(flock_id=flock))==1
    assert r.get_flock_transactions(flock_id=flock).iloc[0].TRANSACTION_TYPE=='Count'
    assert r.get_flock_transactions(flock_id=flock).iloc[0].QUANTITY==0
    assert len(r.get_record_revisions())==len(r._migration_review_audit)==1
    pd.testing.assert_frame_equal(before,r._flocks.drop(columns=['BIRD_COUNT','UPDATED_AT']))
    assert r.get_flock_events(flock).empty
    report=build_custom_report(r,user=user(),dataset='Flocks',selected_fields=['FLOCK_ID','BIRD_COUNT'])
    assert report.iloc[0]['Bird Count']==0
    csv=pd.read_csv(BytesIO(report_csv(user(),report)))
    xlsx=pd.read_excel(BytesIO(report_xlsx(user(),report)))
    assert csv['Bird Count'].notna().all() and csv['Bird Count'].tolist()==[0]
    assert xlsx['Bird Count'].notna().all() and xlsx['Bird Count'].tolist()==[0]


@pytest.mark.parametrize('quantity',[-1,-.1,.5,Decimal('0.0000000000000001'),float('nan'),float('inf'),None,True,'bad'])
def test_current_count_rejects_invalid_values_without_any_write(chain,quantity):
    r,a,o,f,q,flock,record=chain
    before=r._flocks.copy(deep=True)
    with pytest.raises(RepositoryError):
        r.record_current_flock_quantity(payload(flock,quantity),'invalid',r.get_flock(flock)['UPDATED_AT'],'Synthetic',confirmed=True,actor=ACTOR)
    pd.testing.assert_frame_equal(before,r._flocks)
    assert r._flock_transactions.empty and r.get_record_revisions().empty and not r._migration_review_audit


@pytest.mark.parametrize('kind',['Removal','Delivery','Sale'])
def test_zero_does_not_relax_other_types(chain,kind):
    r,a,o,f,q,flock,record=chain
    assert validate_flock_transaction(r,payload(flock,0,kind),current_count=True)
    with pytest.raises(RepositoryError):
        r.record_current_flock_quantity(payload(flock,0,kind),'invalid-kind',r.get_flock(flock)['UPDATED_AT'],'Synthetic',confirmed=True,actor=ACTOR)
    assert r.get_flock(flock)['BIRD_COUNT']==10 and r._flock_transactions.empty


def test_unconfirmed_count_zero_and_removal_overdraw_stay_rejected(chain):
    r,a,o,f,q,flock,record=chain
    assert validate_flock_transaction(r,payload(flock))
    with pytest.raises(ValueError): r.upsert_flock_transaction(payload(flock))
    with pytest.raises(RepositoryError):
        r.record_current_flock_quantity(payload(flock),'not-confirmed',r.get_flock(flock)['UPDATED_AT'],'Synthetic',confirmed=False,actor=ACTOR)
    with pytest.raises(RepositoryError,match='exceeds'):
        r.record_current_flock_quantity(payload(flock,11,'Removal'),'overdraw',r.get_flock(flock)['UPDATED_AT'],'Synthetic',confirmed=True,actor=ACTOR)
    assert r.get_flock(flock)['BIRD_COUNT']==10 and r._flock_transactions.empty


def test_zero_observation_does_not_clear_other_flocks_in_shared_account(chain):
    r,a,o,f,q,flock,record=chain
    second=r.upsert_flock(dict(record,FLOCK_NUMBER='DEV_TEST other flock',PERMIT_NUMBER='DEV_TEST other permit',BIRD_COUNT=5))
    r.record_current_flock_quantity(payload(flock),'zero-one-flock',r.get_flock(flock)['UPDATED_AT'],'Observed zero',confirmed=True,actor=ACTOR)
    assert r.get_flock(second)['BIRD_COUNT']==5
    assert account_usage_context(r,a)['summaries'][0]['known_bird_count']==5


def test_zero_count_ui_save_refresh_and_account_summary(chain,tmp_path,monkeypatch):
    r,a,o,f,q,flock,record=chain
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local');monkeypatch.setenv('REPOSITORY_MODE','mock')
    root=Path(__file__).resolve().parents[1]
    app=authenticated_app(root/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    app.session_state['_efns_record_6_Flock_Transactions_view']='new'
    app.switch_page('app/pages/6_Flock_Transactions.py').run()
    assert not app.exception
    app.number_input(key='flock_tx_form_quantity').set_value(0)
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and app.error and r._flock_transactions.empty
    assert app.number_input(key='flock_tx_form_quantity').value==0
    app.checkbox(key='flock_tx_form_apply_'+flock).check()
    app.text_input(key='flock_tx_form_quantity_reason').input('Observed zero — synthetic acceptance')
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_flock_transactions(flock_id=flock))==1 and r.get_flock(flock)['BIRD_COUNT']==0
    app.run()
    assert len(r.get_record_revisions())==len(r._migration_review_audit)==1
    app.session_state['_efns_record_5_Flocks_view']='detail'
    app.session_state['_efns_record_5_Flocks_id']=flock
    app.switch_page('app/pages/5_Flocks.py').run()
    app.button(key='flock_record_refresh').click().run()
    assert not app.exception and not app.error
    assert any(m.label=='Known Bird Count' and Decimal(m.value)==0 for m in app.metric)
    assert any(m.label=='Account usage' and m.value=='Cannot calculate' for m in app.metric)
