"""Draft failures cannot block the actual record workspace; AppTest/Mock only."""
from pathlib import Path

import pandas as pd
import pytest

from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain


def unavailable(*args,**kwargs):
    raise RuntimeError('DEV_TEST draft failure')


@pytest.mark.parametrize('page,key,which',[
    ('3_Accounts_Facilities_Flocks.py','3_Accounts_Facilities_Flocks','account'),
    ('5_Flocks.py','5_Flocks','flock'),('7_Quota_Registrations.py','7_Quota_Registrations','quota')])
def test_position_failure_leaves_detail_usable(chain,tmp_path,monkeypatch,page,key,which):
    repo,account,other,facility,quota,flock,*_=chain
    before=repo._flocks.copy(deep=True)
    from app.services import quota_usage
    monkeypatch.setattr(quota_usage,'quota_position',unavailable)
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.session_state['_efns_record_'+key+'_view']='detail'
    app.session_state['_efns_record_'+key+'_id']={'account':account,'flock':flock,'quota':quota}[which]
    app.switch_page('app/pages/'+page).run()
    assert not app.exception and not app.error
    assert sum(c.value=='Calculation draft unavailable for this record' for c in app.caption)==1
    assert any(m.label=='Usage percentage' and m.value=='Not established' for m in app.metric)
    assert any(b.label=='Edit' for b in app.button)
    pd.testing.assert_frame_equal(repo._flocks,before)


def test_stock_failure_keeps_flock_details(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,flock,*_=chain
    import data.flock_stock
    monkeypatch.setattr(data.flock_stock,'flock_stock',unavailable)
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.session_state['_efns_record_5_Flocks_view']='detail'
    app.session_state['_efns_record_5_Flocks_id']=flock
    app.switch_page('app/pages/5_Flocks.py').run()
    assert not app.exception and not app.error
    assert any(c.value=='Calculation draft unavailable for this record' for c in app.caption)
    assert any('**Bird Count**' in m.value and '10' in m.value for m in app.markdown)
    assert any(b.label=='View Account' for b in app.button)


def test_component_failure_keeps_transaction_list(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,*_=chain
    target=repo.upsert_quota_transaction(dict(QUOTA_ID=quota,TRANSACTION_TYPE='Purchase',
        QUOTA_COUNT=2,PRICE=None,RELATED_ACCOUNT_ID=other,EFFECTIVE_DATE='2026-01-01'))
    from data import quota_position
    monkeypatch.setattr(quota_position,'component_table',unavailable)
    app=authenticated_app(Path(__file__).resolve().parents[1]/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/8_Quota_Transactions.py').run()
    assert not app.exception and not app.error
    assert sum(c.value=='Calculation draft unavailable for this record' for c in app.caption)==1
    assert target in app.session_state.quota_tx_list_row_ids
