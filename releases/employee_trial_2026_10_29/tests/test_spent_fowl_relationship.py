"""Synthetic-only nullable Account lookup, revision, replay and UI regressions."""
from pathlib import Path
from uuid import uuid4
import pandas as pd
import pytest
from data.account_relationships import FIELD,resolve_spent_fowl_source,account_link_options
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository,MODEL
from data.repositories.base import RepositoryError,ConcurrencyError
from tests.test_staff_workflows import chain
from tests.test_round2 import _app,_open
from tests.test_account_usage_quantity import ACTOR

@pytest.fixture
def accounts():
 r=MockRepository();a=r.upsert_account({'ORGANIZATION_NAME':'Synthetic source','SPENT_FOWL_PLANS':'Retained legacy evidence'})
 target=r.upsert_account({'ORGANIZATION_NAME':'Synthetic destination'})
 return r,a,target

@pytest.mark.parametrize('value',[None,pd.NA,float('nan'),'','null','None'])
def test_optional_clear_is_true_null(accounts,value):
 r,a,t=accounts
 r.upsert_account({'ACCOUNT_ID':a,FIELD:t})
 r.upsert_account({'ACCOUNT_ID':a,FIELD:value})
 assert r.get_account(a).get(FIELD) is None
 assert r.get_account(a)['SPENT_FOWL_PLANS']=='Retained legacy evidence'

def test_link_update_clear_revision_replay_and_cas(accounts):
 r,a,t=accounts;before=r.get_account(a);version=before['UPDATED_AT']
 result=r.revise_record('ACCOUNT',a,{FIELD:t},'Source GUID reviewed','lookup-1',actor=ACTOR,expected_updated_at=version)
 assert result==a and r.get_account(a)[FIELD]==t
 assert r.get_account(a)['SPENT_FOWL_PLANS']==before['SPENT_FOWL_PLANS']
 n=len(r.get_record_revisions());audits=len(r._migration_review_audit);r.revise_record('ACCOUNT',a,{FIELD:t},'Source GUID reviewed','lookup-1',actor=ACTOR,expected_updated_at=version)
 assert len(r.get_record_revisions())==n and len(r._migration_review_audit)==audits
 with pytest.raises(ConcurrencyError):r.revise_record('ACCOUNT',a,{FIELD:None},'New change','lookup-stale',actor=ACTOR,expected_updated_at=version)
 r.revise_record('ACCOUNT',a,{FIELD:None},'Explicit clear','lookup-2',actor=ACTOR,expected_updated_at=r.get_account(a)['UPDATED_AT'])
 assert r.get_account(a)[FIELD] is None

@pytest.mark.parametrize('value',['A display name',str(uuid4())])
def test_invalid_and_missing_targets_rejected_before_save(accounts,value):
 r,a,t=accounts
 with pytest.raises(RepositoryError):r.upsert_account({'ACCOUNT_ID':a,FIELD:value})
 with pytest.raises(RepositoryError):r.revise_record('ACCOUNT',a,{FIELD:value},'Reason','invalid',actor=ACTOR,expected_updated_at=r.get_account(a)['UPDATED_AT'])
 assert not r.get_account(a).get(FIELD)

def test_link_prevents_deletion(accounts):
 r,a,t=accounts;r.upsert_account({'ACCOUNT_ID':a,FIELD:t})
 with pytest.raises((RepositoryError,ValueError)):r.delete_account(t)
 assert r.get_account(t) is not None

def test_original_guid_wins_but_conflicting_label_holds(accounts):
 r,a,t=accounts;frame=r.get_accounts()
 resolved=resolve_spent_fowl_source({'EFNS_SPENTFOWLPLANS':t,'EFNS_SPENTFOWLPLANSNAME':'Synthetic destination'},frame)
 assert resolved['status']=='SOURCE_GUID' and resolved['target_id']==t
 assert resolve_spent_fowl_source({'efns_spentfowlplans':t,'efns_spentfowlplansname':'Different'},frame)['status']=='GUID_LABEL_CONFLICT'
 assert resolve_spent_fowl_source({},frame)['status']=='NO_CHANGE'

def test_names_never_become_auto_guid_even_unique(accounts):
 r,a,t=accounts
 resolved=resolve_spent_fowl_source({'efns_spentfowlplansname':'Synthetic destination'},r.get_accounts())
 assert resolved['target_id'] is None and resolved['candidates']==[t]
 r.upsert_account({'ORGANIZATION_NAME':'Synthetic destination'})
 assert len(resolve_spent_fowl_source({'efns_spentfowlplansname':'Synthetic destination'},r.get_accounts())['candidates'])==2

def test_snowflake_write_has_same_reference_check(monkeypatch):
 r=SnowflakeRepository(object());target=str(uuid4());saved=[]
 monkeypatch.setattr(r,'get_account',lambda key: {'ACCOUNT_ID':target} if key==target else None)
 monkeypatch.setattr(r,'_upsert',lambda table,record,**kw:saved.append(record) or 'new')
 r.upsert_account({'ORGANIZATION_NAME':'Synthetic',FIELD:target})
 assert saved[0][FIELD]==target
 with pytest.raises(RepositoryError):r.upsert_account({FIELD:str(uuid4())})
 assert FIELD in MODEL['ACCOUNT'][1].split()

def test_unavailable_old_value_is_an_option_not_silently_cleared(accounts):
 r,a,t=accounts;unknown=str(uuid4())
 assert unknown in account_link_options(r.get_accounts(),unknown).values()

def test_account_page_link_navigation_and_comment_only_edit(chain,tmp_path,monkeypatch):
 r,a,target,*_=chain
 r.upsert_account({'ACCOUNT_ID':a,FIELD:target,'SPENT_FOWL_PLANS':'Retained text'})
 app=_app(r,tmp_path,monkeypatch)
 app=_open(app,'app/pages/3_Accounts_Facilities_Flocks.py',a,'detail')
 assert not app.exception
 assert any(x.label=='Open Spent Fowl Plans' for x in app.button)
 next(x for x in app.button if x.label=='Open Spent Fowl Plans').click().run()
 assert not app.exception and app.session_state['_efns_record_3_Accounts_Facilities_Flocks_id']==target
 app=_open(app,'app/pages/3_Accounts_Facilities_Flocks.py',a,'edit')
 assert not app.exception
 assert app.selectbox(key='account_form_spent_fowl_account').value
 app.text_area(key='account_form_description').input('Only description changed')
 app.text_input(key='account_form_revision_reason').input('Synthetic reason')
 app.button(key='account_record_save').click().run()
 assert not app.exception and not app.error
 assert r.get_account(a)[FIELD]==target and r.get_account(a)['SPENT_FOWL_PLANS']=='Retained text'


def test_audit_failure_rolls_back_lookup_and_revision(accounts,monkeypatch):
 import data.record_safety as safety
 r,a,t=accounts;before=r.get_account(a);n=len(r.get_record_revisions())
 def fail(*args,**kwargs):raise RepositoryError('Synthetic audit failure')
 monkeypatch.setattr(safety,'history_audit',fail)
 with pytest.raises(RepositoryError,match='Synthetic audit failure'):
  r.revise_record('ACCOUNT',a,{FIELD:t},'Reviewed','audit-fails',actor=ACTOR,expected_updated_at=before['UPDATED_AT'])
 assert not r.get_account(a).get(FIELD) and r.get_account(a)['UPDATED_AT']==before['UPDATED_AT']
 assert len(r.get_record_revisions())==n


def test_viewer_cannot_save_lookup(accounts):
 from app.services.authorized_repository import AuthorizedRepository
 from tests.test_report_center import user
 r,a,t=accounts
 wrapped=AuthorizedRepository(r,object(),user())
 with pytest.raises(RepositoryError,match='permission'):
  wrapped.revise_record('ACCOUNT',a,{FIELD:t},'Reviewed','not-authorized',expected_updated_at=r.get_account(a)['UPDATED_AT'])
 assert not r.get_account(a).get(FIELD)


def test_quota_presentation_distinguishes_two_unknown_definitions(chain,tmp_path,monkeypatch):
 r,a,*_=chain;app=_app(r,tmp_path,monkeypatch)
 app=_open(app,'app/pages/3_Accounts_Facilities_Flocks.py',a,'detail')
 assert not app.exception
 labels={m.label:m.value for m in app.metric}
 assert labels['Current usable quota']=='Not established'
 assert labels['Current occupancy']=='Not established'
 assert labels['Usage percentage']=='Not established'


def test_explicit_ui_clear_preserves_legacy_text(chain,tmp_path,monkeypatch):
 r,a,target,*_=chain;r.upsert_account({'ACCOUNT_ID':a,FIELD:target,'SPENT_FOWL_PLANS':'Retained text'})
 app=_open(_app(r,tmp_path,monkeypatch),'app/pages/3_Accounts_Facilities_Flocks.py',a,'edit')
 app.selectbox(key='account_form_spent_fowl_account').select('Not selected')
 app.text_input(key='account_form_revision_reason').input('Explicitly cleared synthetic lookup')
 app.button(key='account_record_save').click().run()
 assert not app.exception and not app.error
 assert r.get_account(a)[FIELD] is None and r.get_account(a)['SPENT_FOWL_PLANS']=='Retained text'


def test_stored_bird_count_is_not_exposed_as_verified_current_occupancy(chain):
 from app.services.quota_usage import account_usage_context
 r,a,*_=chain
 rows=account_usage_context(r,a)['summaries']
 assert any(x['known_bird_count'] is not None for x in rows)
 assert all(x['current_occupancy'] is None and x['usage_percent'] is None for x in rows)


@pytest.mark.parametrize('null',[None,pd.NA,float('nan')])
def test_empty_stored_lookup_opens_edit_as_not_selected(chain,tmp_path,monkeypatch,null):
 r,a,*_=chain
 if FIELD not in r._accounts:r._accounts[FIELD]=None
 r._accounts[FIELD]=r._accounts[FIELD].astype(object)
 r._accounts.loc[r._accounts.ACCOUNT_ID==a,FIELD]=null
 app=_open(_app(r,tmp_path,monkeypatch),'app/pages/3_Accounts_Facilities_Flocks.py',a,'edit')
 assert not app.exception
 assert app.selectbox(key='account_form_spent_fowl_account').value=='Not selected'
