"""Permit-only entry and role-account names using isolated synthetic data."""
from copy import deepcopy
import datetime as dt
import json

import pandas as pd
import pytest

from app.services.flock_form_fields import duplicate_permit_errors, role_account_names
from tests.test_flocks_accounts_legacy_labels import open_page, ENTRIES
from tests.test_staff_workflows import chain


@pytest.fixture
def form_chain(chain):
    repo,account,_,facility,_,flock,_=chain
    for name,flags in [('Synthetic Hatchery',{'HATCHERY_ROLE':True}),
                       ('Synthetic Breeder',{'BREEDER_ROLE':True}),
                       ('Synthetic Both',{'HATCHERY_ROLE':True,'BREEDER_ROLE':True}),
                       ('Synthetic Neither',{'HATCHERY_ROLE':False,'BREEDER_ROLE':False})]:
        repo.upsert_account(dict(ORGANIZATION_NAME=name,REGISTRATION_NUMBER=name,
            STATUS='Active',**flags))
    repo._flocks['FLOCK_NUMBER']='NF'
    repo._flocks['PERMIT_NUMBER']='SYN EXISTING'
    repo._flocks['HATCHERY']='Historical Hatchery outside Accounts'
    repo._flocks['BREEDER']=' Historical Breeder '
    return repo,account,facility,flock


def new_form(data,tmp_path,monkeypatch,entry,prefix):
    app=open_page(data,tmp_path,monkeypatch,entry,prefix,'flock')
    app.button(key='flock_list_new').click().run()
    assert not app.error and not app.exception
    return app


def test_role_account_names_are_exact_role_filtered_and_nullable():
    frame=pd.DataFrame([
        dict(ORGANIZATION_NAME='  Exact Name  ',HATCHERY_ROLE=True),
        dict(ORGANIZATION_NAME='Not a hatchery',HATCHERY_ROLE=False),
        dict(ORGANIZATION_NAME='Unknown flag',HATCHERY_ROLE=pd.NA),
        dict(ORGANIZATION_NAME='Text false',HATCHERY_ROLE='False'),
        dict(ORGANIZATION_NAME=None,HATCHERY_ROLE=True),
        dict(ORGANIZATION_NAME='None',HATCHERY_ROLE=True),
        dict(ORGANIZATION_NAME='  Exact Name  ',HATCHERY_ROLE=True)])
    before=frame.copy(deep=True)
    assert role_account_names(frame,'HATCHERY_ROLE')==(None,'  Exact Name  ','None')
    assert role_account_names(frame,'BREEDER_ROLE')==(None,)
    pd.testing.assert_frame_equal(frame,before)


def test_duplicate_permit_normalizes_only_comparison_and_excludes_current_id(form_chain):
    repo,_,facility,flock=form_chain
    repo._flocks['PERMIT_NUMBER']='  SyN EXisting '
    before=repo._flocks.copy(deep=True)
    args=(repo.get_flocks(),repo.get_accounts(),repo.get_facilities())
    errors=duplicate_permit_errors('syn existing',*args)
    assert len(errors)==1
    assert 'DEV_TEST staff producer' in errors[0] and 'DEV_TEST barn' in errors[0]
    assert 'Registration Number 001' in errors[0]
    assert not duplicate_permit_errors('SYN EXISTING',*args,current_id=flock)
    assert not duplicate_permit_errors('',*args)
    pd.testing.assert_frame_equal(before,repo._flocks)


@pytest.mark.parametrize('value',['None','NULL','NaN','NaT'])
def test_duplicate_permit_keeps_literal_words_as_identifiers(form_chain,value):
    repo,_,_,_=form_chain
    repo._flocks['PERMIT_NUMBER']='  '+value+' '
    assert duplicate_permit_errors(value.lower(),repo.get_flocks(),repo.get_accounts(),repo.get_facilities())


@pytest.mark.parametrize('entry,prefix',ENTRIES)
def test_identifier_removed_from_default_list_summary_details_and_form(form_chain,tmp_path,monkeypatch,entry,prefix):
    repo,_,_,flock=form_chain;before=repo._flocks.copy(deep=True)
    app=open_page(form_chain,tmp_path,monkeypatch,entry,prefix,'flock')
    grid=app.dataframe[0]
    assert json.loads(grid.proto.columns)['FLOCK_NUMBER']['hidden']
    assert grid.value.iloc[0].FLOCK_NUMBER=='NF'  # Raw/export data is retained.
    assert grid.proto.placeholder=='—'  # Preserve the already merged null display.
    app.session_state['_efns_record_5_Flocks_view']='detail'
    app.session_state['_efns_record_5_Flocks_id']=flock
    app.run()
    assert not app.error and not app.exception
    assert not any('Flock Number' in block.value for block in app.markdown)
    assert any('<h1 class="efns-page-title">SYN EXISTING</h1>' in block.value for block in app.markdown)
    fields=next(grid.value.Field.tolist() for grid in app.dataframe if 'Field' in grid.value)
    assert 'Flock Number' not in fields and 'Permit Number' in fields
    app.button(key='flock_record_edit').click().run()
    assert 'flock_form_number' not in [widget.key for widget in app.text_input]
    assert app.text_input(key='flock_form_permit').disabled
    assert any('Permit Number cannot be changed here' in block.value for block in app.caption)
    assert app.selectbox(key='flock_form_hatchery').value=='Historical Hatchery outside Accounts'
    assert app.selectbox(key='flock_form_breeder').value==' Historical Breeder '
    pd.testing.assert_frame_equal(before,repo._flocks)


@pytest.mark.parametrize('entry,prefix',ENTRIES)
def test_create_permit_only_and_hatchery_breeder_round_trip(form_chain,tmp_path,monkeypatch,entry,prefix):
    repo,_,_,_=form_chain
    app=new_form(form_chain,tmp_path,monkeypatch,entry,prefix)
    assert 'flock_form_number' not in [widget.key for widget in app.text_input]
    assert not app.text_input(key='flock_form_permit').disabled
    assert app.selectbox(key='flock_form_hatchery').options==['—','Synthetic Both','Synthetic Hatchery']
    assert app.selectbox(key='flock_form_breeder').options==['—','Synthetic Both','Synthetic Breeder']
    app.button(key='flock_record_save').click().run()
    assert any(error.value=='Permit Number is required.' for error in app.error)
    assert not any('Flock Number' in error.value for error in app.error)
    app.text_input(key='flock_form_permit').input(' SYN NEW ')
    app.number_input(key='flock_form_birds').set_value(12)
    app.selectbox(key='flock_form_hatchery').select('Synthetic Hatchery')
    app.selectbox(key='flock_form_breeder').select('Synthetic Breeder')
    app.button(key='flock_record_save').click().run()
    assert not app.error and not app.exception
    fid=app.session_state['_efns_record_5_Flocks_id']
    row=repo.get_flock(fid)
    assert row['PERMIT_NUMBER']==row['FLOCK_NUMBER']=='SYN NEW'
    assert row['HATCHERY']=='Synthetic Hatchery' and row['BREEDER']=='Synthetic Breeder'
    assert repo.get_flock_transactions(fid).empty
    revision=repo.get_record_revisions().iloc[0]
    assert revision.CHANGE_KIND=='CREATE' and revision.AFTER_DATA['FLOCK_NUMBER']=='SYN NEW'
    app.button(key='flock_record_edit').click().run()
    app.selectbox(key='flock_form_hatchery').select('Synthetic Both')
    app.selectbox(key='flock_form_breeder').select_index(0)
    app.text_input(key='flock_form_revision_reason').input('Synthetic role name correction')
    app.button(key='flock_record_save').click().run()
    assert not app.error and not app.exception
    row=repo.get_flock(fid)
    assert row['HATCHERY']=='Synthetic Both' and row['BREEDER'] is None
    assert row['FLOCK_NUMBER']==row['PERMIT_NUMBER']=='SYN NEW'
    correction=repo.get_record_revisions().iloc[-1]
    assert correction.CHANGE_KIND=='ATTRIBUTE_CORRECTION'
    assert correction.BEFORE_DATA['BREEDER']=='Synthetic Breeder'
    assert correction.AFTER_DATA['BREEDER'] is None


@pytest.mark.parametrize('entry,prefix',ENTRIES)
def test_duplicate_create_is_blocked_with_account_and_facility(form_chain,tmp_path,monkeypatch,entry,prefix):
    repo,_,_,_=form_chain
    repo._flocks['PERMIT_NUMBER']='  SyN EXISTING '
    repo._flocks['STATUS']='Depopulated'
    before=repo._flocks.copy(deep=True)
    app=new_form(form_chain,tmp_path,monkeypatch,entry,prefix)
    app.text_input(key='flock_form_permit').input('syn existing')
    app.number_input(key='flock_form_birds').set_value(5)
    app.button(key='flock_record_save').click().run()
    assert not app.exception
    assert any('already used' in error.value and 'DEV_TEST staff producer' in error.value
        and 'DEV_TEST barn' in error.value for error in app.error)
    pd.testing.assert_frame_equal(before,repo._flocks)
    assert repo.get_record_revisions().empty


@pytest.mark.parametrize('entry,prefix',ENTRIES)
def test_legacy_duplicates_and_tampered_readonly_permit_do_not_rewrite_identifiers(form_chain,tmp_path,monkeypatch,entry,prefix):
    import app.services.flock_form_fields as fields
    repo,_,_,flock=form_chain
    old=repo._flocks.iloc[0].to_dict()
    repo._flocks=pd.DataFrame([old,dict(old,FLOCK_ID='synthetic-duplicate',FLOCK_NUMBER='Other legacy number')])
    written=[];revise=repo.revise_record
    def track(entity,record_id,changes,*args,**kwargs):
        written.append(deepcopy(changes));return revise(entity,record_id,changes,*args,**kwargs)
    monkeypatch.setattr(repo,'revise_record',track)
    def forbidden(*args,**kwargs):raise AssertionError('Duplicate checking must not run on edit')
    monkeypatch.setattr(fields,'duplicate_permit_errors',forbidden)
    app=open_page(form_chain,tmp_path,monkeypatch,entry,prefix,'flock','edit')
    assert app.text_input(key='flock_form_permit').disabled
    app.text_input(key='flock_form_permit').set_value('ATTEMPTED PERMIT CHANGE')
    app.text_area(key='flock_form_comments').input('Synthetic comment correction')
    app.text_input(key='flock_form_revision_reason').input('Comment only')
    app.button(key='flock_record_save').click().run()
    assert not app.error and not app.exception
    assert written==[{'COMMENTS':'Synthetic comment correction'}]
    row=repo.get_flock(flock)
    for field in ('FLOCK_NUMBER','PERMIT_NUMBER','HATCHERY','BREEDER'):
        assert row[field]==old[field]
    assert repo.get_flock('synthetic-duplicate')['FLOCK_NUMBER']=='Other legacy number'


@pytest.mark.parametrize('entry,prefix',ENTRIES)
@pytest.mark.parametrize('initial',[False,True])
def test_duplicate_guard_preserves_same_creation_request_retry(form_chain,tmp_path,monkeypatch,entry,prefix,initial):
    import app.services.form_safety as safety
    repo,_,_,_=form_chain
    # Keep the successful form open to exercise a retry after navigation failed.
    monkeypatch.setattr(safety,'open_saved_record',lambda record_id:None)
    app=new_form(form_chain,tmp_path,monkeypatch,entry,prefix)
    app.text_input(key='flock_form_permit').input('SYN RETRY')
    app.number_input(key='flock_form_birds').set_value(12)
    app.date_input(key='flock_form_hatch').set_value(dt.date(2026,1,1)).run()
    if initial:
        app.checkbox(key='flock_form_initial_confirmed').check()
        app.text_input(key='flock_form_initial_reason').input('Synthetic placement evidence')
    app.button(key='flock_record_save').click().run()
    assert not app.error and not app.exception, [error.value for error in app.error]
    rows=repo.get_flocks();fid=rows.loc[rows.PERMIT_NUMBER.eq('SYN RETRY')].iloc[0].FLOCK_ID
    history_before=repo.get_record_revisions().copy(deep=True)
    app.button(key='flock_record_save').click().run()
    assert not app.error and not app.exception
    assert len(repo.get_flocks())==len(rows)
    pd.testing.assert_frame_equal(history_before,repo.get_record_revisions())
    if initial:assert len(repo.get_flock_events(fid))==1
    else:
        audits=[row for row in repo._migration_review_audit if row['ENTITY_ID']==fid]
        assert len(audits)==1 and audits[0]['ACTION']=='CREATE'
        # A different payload is a new creation attempt, not a bypassable retry.
        app.selectbox(key='flock_form_breeder').select('Synthetic Breeder')
        app.button(key='flock_record_save').click().run()
        assert any('already used' in error.value for error in app.error)
        assert len(repo.get_flocks())==len(rows)
