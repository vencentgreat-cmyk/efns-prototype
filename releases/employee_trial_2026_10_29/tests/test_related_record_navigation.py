"""Isolated AppTest coverage for the Account/Facility/Flock/Delivery route."""
from copy import deepcopy
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

import app.navigation as navigation
import app.auth as auth
from app.security import AuthorizationError, Permission
from tests.auth_support import authenticated_app


@pytest.mark.parametrize('entrypoint,page_prefix', [
    ('streamlit_app.py','app/pages'),
    ('app/Home.py','pages'),
])
@pytest.mark.parametrize('environment_prefix', [None, 'pages', 'stale/pages'])
def test_account_facility_flock_delivery_related_navigation(tmp_path,monkeypatch,entrypoint,page_prefix,environment_prefix):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local')
    monkeypatch.setenv('REPOSITORY_MODE','mock')
    # A stale process prefix must not affect either entrypoint's page lookup.
    if environment_prefix is None:
        monkeypatch.delenv('EFNS_PAGE_PREFIX',raising=False)
    else:
        monkeypatch.setenv('EFNS_PAGE_PREFIX',environment_prefix)
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch)
    assert not app.exception
    memory=app.session_state.repo.repository
    flock=memory._flocks.iloc[0].to_dict()
    facility=memory._facilities[memory._facilities.FACILITY_ID==flock['FACILITY_ID']].iloc[0].to_dict()
    facility['FACILITY_NAME']='7169 - 6'
    flock['FLOCK_NUMBER']='40053'
    delivery=memory._flock_transactions.iloc[0].to_dict()
    delivery.update(FLOCK_ID=flock['FLOCK_ID'],TRANSACTION_TYPE='Delivery',QUANTITY=22027,
                    TRANSACTION_DATE=date(2018,8,16),NOTES='Synthetic navigation regression')
    decoy={**delivery,'FLOCK_TRANSACTION_ID':'synthetic-decoy','QUANTITY':999,'TRANSACTION_TYPE':'Adjustment'}
    memory._facilities=pd.DataFrame([facility])
    memory._flocks=pd.DataFrame([flock])
    memory._flock_transactions=pd.DataFrame([decoy,delivery])
    before={key:deepcopy(getattr(memory,key)) for key in ('_accounts','_facilities','_flocks','_flock_transactions')}
    # AppTest cannot click dataframe rows. Simulate single-row selection only;
    # real page buttons and st.switch_page execute unchanged.
    monkeypatch.setattr(navigation,'selected_row_index',lambda key:1 if key=='flock_related_Flock_Transactions' else 0)
    account_scope='3_Accounts_Facilities_Flocks'
    app.session_state[navigation._view_key(account_scope,'view')]='detail'
    app.session_state[navigation._view_key(account_scope,'id')]=flock['ACCOUNT_ID']
    app.switch_page(f'{page_prefix}/3_Accounts_Facilities_Flocks.py').run()
    assert not app.exception
    app.button(key='account_related_open_Facilities').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_11_Facilities_id']==facility['FACILITY_ID']
    # AppTest retains its explicitly selected page across run() calls even
    # after the app switches pages; synchronize before the next interaction.
    app.switch_page(f'{page_prefix}/11_Facilities.py').run()
    app.button(key='facility_related_Flocks_open').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_5_Flocks_id']==flock['FLOCK_ID']
    app.switch_page(f'{page_prefix}/5_Flocks.py').run()
    app.button(key='flock_related_Flock_Transactions_open').click().run()
    assert not app.exception
    assert not app.error
    assert app.session_state['_efns_record_6_Flock_Transactions_view']=='detail'
    assert app.session_state['_efns_record_6_Flock_Transactions_id']==delivery['FLOCK_TRANSACTION_ID']
    assert any('Delivery' in block.value for block in app.markdown)
    assert any('22027' in block.value for block in app.markdown)
    assert any('2018-08-16' in block.value for block in app.markdown)
    assert not any('999' == block.value for block in app.markdown)
    app.switch_page(f'{page_prefix}/6_Flock_Transactions.py').run()
    app.button(key='flock_tx_record_edit').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_6_Flock_Transactions_view']=='edit'
    app.button(key='flock_tx_record_cancel').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_6_Flock_Transactions_view']=='detail'
    related_flock=next(button for button in app.button if button.label=='Open related Flock')
    related_flock.click().run()
    assert not app.exception
    assert app.session_state['_efns_record_5_Flocks_id']==flock['FLOCK_ID']
    app.switch_page(f'{page_prefix}/5_Flocks.py').run()
    app.button(key='flock_parent_facility').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_11_Facilities_id']==facility['FACILITY_ID']
    app.switch_page(f'{page_prefix}/11_Facilities.py').run()
    app.button(key='facility_parent_account').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_3_Accounts_Facilities_Flocks_id']==facility['ACCOUNT_ID']
    app.switch_page(f'{page_prefix}/5_Flocks.py').run()
    app.button(key='flock_parent_account').click().run()
    assert not app.exception
    assert app.session_state['_efns_record_3_Accounts_Facilities_Flocks_id']==flock['ACCOUNT_ID']
    for key,frame in before.items():
        pd.testing.assert_frame_equal(frame,getattr(memory,key))


@pytest.mark.parametrize('entrypoint,page_prefix', [
    ('streamlit_app.py','app/pages'), ('app/Home.py','pages'),
])
def test_report_link_and_denied_dashboard_use_registered_pages(tmp_path,monkeypatch,entrypoint,page_prefix):
    root=Path(__file__).resolve().parents[1]
    monkeypatch.setenv('EFNS_RUNTIME_MODE','local')
    monkeypatch.setenv('REPOSITORY_MODE','mock')
    monkeypatch.setenv('EFNS_PAGE_PREFIX','incorrect/pages')
    monkeypatch.setenv('EFNS_ENTRYPOINT','incorrect/Home.py')
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch)
    app.session_state['report_center_open_report']='salmonella-report'
    app.switch_page(f'{page_prefix}/4_Reports.py').run()
    next(button for button in app.button if button.label=='Open Salmonella Test Report').click().run()
    assert not app.exception
    assert any('Salmonella Test Report' in block.value for block in app.markdown)

    original_enforce=auth.enforce_permission
    def deny_operational(user,permission):
        if permission==Permission.VIEW_DATA:
            raise AuthorizationError('Synthetic denied route')
        return original_enforce(user,permission)
    monkeypatch.setattr(auth,'enforce_permission',deny_operational)
    app.switch_page(f'{page_prefix}/5_Flocks.py').run()
    assert any('Access denied' in block.value for block in app.markdown)
    next(button for button in app.button if button.label=='Return to dashboard').click().run()
    assert not app.exception
    assert any('Operations Dashboard' in block.value for block in app.markdown)
