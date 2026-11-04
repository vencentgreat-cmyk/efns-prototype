"""Bounded, readable record history: synthetic Mock/AppTest and captured SQL only."""
import ast
from copy import deepcopy
from decimal import Decimal
from pathlib import Path
import pandas as pd
import pytest
from app.services.revision_history import (
    COLUMNS, record_options, revision_actor_labels, revision_changes,
)
from app.services.authorized_repository import AuthorizedRepository
from app.security import Role,User
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from data.repositories.base import RepositoryError
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain
ROOT=Path(__file__).resolve().parents[1]
ACTOR={'user_id':'DEV_TEST history reviewer','email':'synthetic.history@nsegg.ca'}


def test_matching_history_filters_before_limit_and_returns_latest_copies():
    repo=MockRepository()
    rows=[dict(REVISION_ID=str(i),ENTITY_TYPE=kind,ENTITY_ID=identity,
        RECORDED_AT=f'2026-01-{i+1:02d}T12:00:00',BEFORE_DATA={},AFTER_DATA={'COMMENTS':str(i)})
        for i,(kind,identity) in enumerate([('ACCOUNT','a'),('FLOCK','a'),('ACCOUNT','b'),('ACCOUNT','a'),('ACCOUNT','a')])]
    repo._continuity_rows['RECORD_REVISION']=deepcopy(rows)
    repo.get_record_revisions=lambda:pytest.fail('Unbounded getter must not be used')
    found=repo.get_record_revisions_for('ACCOUNT','a',2)
    assert found.REVISION_ID.tolist()==['4','3']
    assert set(found.ENTITY_TYPE)=={'ACCOUNT'} and set(found.ENTITY_ID)=={'a'}
    found.iloc[0].AFTER_DATA['COMMENTS']='mutated display'
    assert repo._continuity_rows['RECORD_REVISION']==rows
    assert repo.get_record_revisions_for('ACCOUNT','absent').empty


@pytest.mark.parametrize('limit',[0,-1,201,1.5,True,'50'])
def test_history_limit_rejects_unbounded_or_noninteger_input(limit):
    with pytest.raises(RepositoryError,match='History limit'):
        MockRepository().get_record_revisions_for('ACCOUNT','a',limit)


def test_sql_history_is_parameterized_and_bounded_without_global_reader():
    class Fake:
        def query(self,sql,params=None):self.call=(sql,params);return pd.DataFrame()
    fake=Fake();repo=SnowflakeRepository(fake)
    repo._history_rows=lambda *a,**k:pytest.fail('Do not load history then filter')
    identity="DEV_TEST ' OR 1=1 --"
    repo.get_record_revisions_for('ACCOUNT',identity,7)
    sql,params=fake.call
    assert 'FROM EFNS_DEV.APP.RECORD_REVISION WHERE ENTITY_TYPE=%s AND ENTITY_ID=%s' in sql
    assert 'ORDER BY RECORDED_AT DESC' in sql and sql.endswith('LIMIT 7')
    assert params==('ACCOUNT',identity) and identity not in sql
    assert 'BEFORE_DATA' in sql and 'AFTER_DATA' in sql


def test_existing_unfiltered_getter_contract_unchanged():
    repo=MockRepository();repo._continuity_rows['RECORD_REVISION']=[{'ENTITY_TYPE':'ACCOUNT'},{'ENTITY_TYPE':'FLOCK'}]
    assert repo.get_record_revisions().ENTITY_TYPE.tolist()==['ACCOUNT','FLOCK']


def test_history_authorization_is_existing_normal_read_rule():
    class Store:pass
    repo=MockRepository()
    viewer=User('DEV_TEST viewer','synthetic.viewer@nsegg.ca','Synthetic viewer',Role.REPORTING_VIEWER,True,False,'','',None)
    assert AuthorizedRepository(repo,Store(),viewer).get_record_revisions_for('ACCOUNT','a').empty
    inactive=User(viewer.user_id,viewer.email,viewer.display_name,viewer.role,False,False,'','',None)
    with pytest.raises(RepositoryError, match="permission"):
        AuthorizedRepository(repo,Store(),inactive).get_record_revisions_for('ACCOUNT','a')


@pytest.mark.parametrize('encoded',[False,True])
def test_changes_ignore_metadata_preserve_null_zero_and_blank(encoded):
    import json
    before={'COMMENTS':'old','PRICE':0,'TOTAL':None,'EMPTY':'','UPDATED_AT':'old',
            'CREATED_AT':'old','UPDATED_BY':'old','CREATED_BY':'old','_REVISION_REQUEST':'before'}
    after=dict(before,COMMENTS='new',PRICE=None,TOTAL=0,UPDATED_AT='new',CREATED_AT='new',
               UPDATED_BY='new',CREATED_BY='new',_REVISION_REQUEST='after')
    frame=pd.DataFrame([dict(BEFORE_DATA=json.dumps(before) if encoded else before,
        AFTER_DATA=json.dumps(after) if encoded else after,RECORDED_AT='2026-01-10T12:00:00',
        RECORDED_BY='DEV_TEST reviewer',CHANGE_KIND='ATTRIBUTE_CORRECTION',REASON='DEV_TEST reason')])
    original=deepcopy(frame.iloc[0].to_dict())
    result=revision_changes(frame)
    assert list(result)==COLUMNS and set(result.Field)=={'COMMENTS','PRICE','TOTAL'}
    changed=result.set_index('Field')
    assert (changed.loc['PRICE','Old value'],changed.loc['PRICE','New value'])==('0','—')
    assert (changed.loc['TOTAL','Old value'],changed.loc['TOTAL','New value'])==('—','0')
    assert result['Changed at (America/Halifax)'].tolist()==['2026-01-10T08:00:00-04:00']*3
    assert result.Reason.tolist()==['DEV_TEST reason']*3
    assert frame.iloc[0].to_dict()==original


def test_changed_by_resolves_only_page_actor_ids_and_falls_back_to_stored_id():
    known='11111111-1111-1111-1111-111111111111'
    missing='22222222-2222-2222-2222-222222222222'
    frame=pd.DataFrame([
        dict(RECORDED_BY=known,BEFORE_DATA={'COMMENTS':'a'},AFTER_DATA={'COMMENTS':'b'}),
        dict(RECORDED_BY=known,BEFORE_DATA={'COMMENTS':'b'},AFTER_DATA={'COMMENTS':'c'}),
        dict(RECORDED_BY=missing,BEFORE_DATA={'COMMENTS':'c'},AFTER_DATA={'COMMENTS':'d'}),
    ])
    calls=[]
    user=User(known,'known@nsegg.ca','Known Staff',Role.DATA_EDITOR,True,False,'','',None)
    def lookup(user_id):
        calls.append(user_id)
        return user if user_id == known else None
    labels=revision_actor_labels(frame,lookup)
    result=revision_changes(frame,labels)
    assert calls==[known,missing]
    assert labels=={known:'Known Staff',missing:missing}
    assert result['Changed by'].tolist()==['Known Staff','Known Staff',missing]


def test_failed_actor_lookup_keeps_history_and_resolves_other_actors():
    failed='22222222-2222-2222-2222-222222222222'
    known='11111111-1111-1111-1111-111111111111'
    frame=pd.DataFrame([
        dict(RECORDED_BY=failed,BEFORE_DATA={'COMMENTS':'old'},AFTER_DATA={'COMMENTS':'first'}),
        dict(RECORDED_BY=known,BEFORE_DATA={'COMMENTS':'first'},AFTER_DATA={'COMMENTS':'second'}),
    ])
    calls=[]
    def lookup(user_id):
        calls.append(user_id)
        if user_id == failed:
            raise RuntimeError('Synthetic lookup failure')
        return User(known,'known@nsegg.ca','Known Staff',Role.DATA_EDITOR,True,False,'','',None)
    result=revision_changes(frame,revision_actor_labels(frame,lookup))
    assert calls==[failed,known]
    assert result['Changed by'].tolist()==[failed,'Known Staff']
    assert result['Old value'].tolist()==['old','first']
    assert result['New value'].tolist()==['first','second']


def test_record_dropdown_labels_are_type_specific_and_values_remain_full_ids():
    account_id='12345678-1111-2222-3333-444444444444'
    transaction_id='421FEF51-AAAA-BBBB-CCCC-DDDDDDDDDDDD'
    accounts=pd.DataFrame([dict(ACCOUNT_ID=account_id,ORGANIZATION_NAME='Example Eggs',
                                REGISTRATION_NUMBER='A-17')])
    transactions=pd.DataFrame([dict(QUOTA_TRANSACTION_ID=transaction_id,
        TRANSACTION_TYPE='Lease (In)',EFFECTIVE_DATE='2012-09-27',QUOTA_ID='quota-1')])
    account_options=record_options('ACCOUNT',accounts,'ACCOUNT_ID')
    transaction_options=record_options('QUOTA_TRANSACTION',transactions,'QUOTA_TRANSACTION_ID',
                                       {'quota-1':'QR-204'})
    assert account_options=={'Example Eggs · A-17 · 12345678':account_id}
    assert transaction_options=={
        'Lease (In) · 421FEF51 · 2012-09-27 · QR-204':transaction_id,
    }


@pytest.mark.parametrize('before,after',[(None,None),('null','null'),({},{}),({'UPDATED_AT':'a'},{'UPDATED_AT':'b'})])
def test_empty_or_metadata_only_revision_has_placeholder_row(before,after):
    result=revision_changes(pd.DataFrame([dict(BEFORE_DATA=before,AFTER_DATA=after,CHANGE_KIND='CREATE')]))
    assert len(result)==1 and result.Field.iloc[0]=='—'
    assert result['Old value'].iloc[0]=='—' and result['New value'].iloc[0]=='—'
    assert 'BEFORE_DATA' not in result and 'AFTER_DATA' not in result


def test_creation_deletion_and_summer_offset():
    rows=[dict(BEFORE_DATA=None,AFTER_DATA={'PRICE':0,'COMMENTS':''},RECORDED_AT='2026-07-10T12:00:00Z'),
          dict(BEFORE_DATA={'PRICE':Decimal('1.1250')},AFTER_DATA=None)]
    result=revision_changes(pd.DataFrame(rows))
    assert result['New value'].tolist()==['','0','—']
    assert result['Old value'].tolist()==['—','—','1.1250']
    assert result['Changed at (America/Halifax)'].iloc[0]=='2026-07-10T09:00:00-03:00'
    assert revision_changes(pd.DataFrame()).columns.tolist()==COLUMNS


def test_account_revision_visible_in_actual_history_page_without_global_payload(chain,tmp_path,monkeypatch):
    repo,account,*_=chain
    repo.revise_record('ACCOUNT',account,{'DESCRIPTION':'DEV_TEST revised account description'},
        'DEV_TEST reviewed account evidence','DEV_TEST account edit',actor=ACTOR,
        expected_updated_at=repo.get_account(account)['UPDATED_AT'])
    # Large unrelated snapshots never reach the renderer; no real 32 MB fixture.
    repo._continuity_rows['RECORD_REVISION'] += [dict(REVISION_ID='DEV_TEST unrelated '+str(i),
        ENTITY_TYPE='ACCOUNT',ENTITY_ID='DEV_TEST other '+str(i),RECORDED_AT='2026-01-01',
        BEFORE_DATA={'DESCRIPTION':'DEV_TEST payload'*400},AFTER_DATA={'DESCRIPTION':'DEV_TEST larger'*400})
        for i in range(150)]
    repo.get_record_revisions=lambda:pytest.fail('Global history must never be fetched by this page')
    calls=[];original=repo.get_record_revisions_for
    def bounded(entity,record,limit=50):
        calls.append((entity,record,limit));return original(entity,record,limit)
    monkeypatch.setattr(repo,'get_record_revisions_for',bounded)
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/21_Record_History.py').run()
    assert not app.exception and not app.error
    assert 'Change history' in [tab.label for tab in app.tabs]
    app.selectbox(key='history_record_type').select('Account').run()
    selector=app.selectbox(key='history_record_ACCOUNT')
    selector.select(next(label for label in selector.options if account[:8].upper() in label)).run()
    assert not app.exception and not app.error
    history=[f.value for f in app.dataframe if list(f.value)==COLUMNS]
    assert any('DEV_TEST reviewed account evidence' in f.Reason.tolist() for f in history)
    assert any('DEV_TEST revised account description' in f['New value'].tolist() for f in history)
    assert all('BEFORE_DATA' not in f.value and 'AFTER_DATA' not in f.value for f in app.dataframe)
    assert calls and all(e and i and limit==50 for e,i,limit in calls)
    assert any(e=='ACCOUNT' and i==account for e,i,limit in calls)
    assert len(repo._continuity_rows['RECORD_REVISION'])==151
    assert app.selectbox(key='history_record_type').options==['Account','Facility','Facility Detail','Flock',
        'Flock Transaction','Quota Registration','Quota Transaction','Salmonella Test','Production record']


def test_no_global_history_call_left_in_page_source():
    tree=ast.parse((ROOT/'app/pages/21_Record_History.py').read_text(encoding='utf-8'))
    assert not any(isinstance(n,ast.Attribute) and n.attr=='get_record_revisions' for n in ast.walk(tree))


def test_history_default_limit_is_fifty_even_with_more_matching_revisions():
    repo=MockRepository()
    repo._continuity_rows['RECORD_REVISION']=[dict(REVISION_ID=str(i),ENTITY_TYPE='ACCOUNT',ENTITY_ID='a',
        RECORDED_AT=f'2026-01-01T00:{i//60:02d}:{i%60:02d}') for i in range(75)]
    found=repo.get_record_revisions_for('ACCOUNT','a')
    assert len(found)==50 and found.REVISION_ID.tolist()==[str(i) for i in range(74,24,-1)]


def test_empty_history_ui_uses_read_only_info(chain,tmp_path,monkeypatch):
    repo=chain[0]
    repo.get_record_revisions=lambda:pytest.fail('Do not fetch the full revision table')
    before=deepcopy(repo._continuity_rows)
    app=authenticated_app(ROOT/'streamlit_app.py',tmp_path,monkeypatch)
    app.session_state['_base_repo']=repo
    app.switch_page('app/pages/21_Record_History.py').run()
    assert not app.exception and not app.error
    assert any(info.value=='No recorded changes for this record yet.' for info in app.tabs[4].info)
    assert repo._continuity_rows==before
