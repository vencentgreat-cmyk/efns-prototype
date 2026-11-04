"""Exact registration disambiguation by stored Account status; no name matching."""
import pandas as pd
import pytest

from data.producer_identity import resolve_producer


def accounts(statuses=('Active','Inactive')):
    return pd.DataFrame([
        dict(ACCOUNT_ID='active-id',REGISTRATION_NUMBER='7402',
             ORGANIZATION_NAME='Six Maples Farm',STATUS=statuses[0]),
        dict(ACCOUNT_ID='inactive-id',REGISTRATION_NUMBER='7402',
             ORGANIZATION_NAME='Six Maples Farm INACTIVE',STATUS=statuses[1]),
    ])


@pytest.mark.parametrize('statuses',[('Active','Inactive'),('aCtIvE','INACTIVE')])
def test_one_active_registration_match_ignores_inactive_duplicate(statuses):
    frame=accounts(statuses)
    before=frame.copy(deep=True)
    result=resolve_producer({'PRODUCER_NUMBER':'7402'},frame)
    assert result['status']=='UNIQUE_MATCHED'
    assert result['account_id']=='active-id'
    assert result['method']=='EXACT_REGISTRATION_NUMBER_ACTIVE_ONLY'
    assert 'inactive-id' in result['basis']
    assert result['source_number']=='7402'
    pd.testing.assert_frame_equal(frame,before)


@pytest.mark.parametrize('statuses',[('Active','Active'),('Inactive','Inactive')])
def test_ambiguous_active_count_stays_multiple(statuses):
    result=resolve_producer({'PRODUCER_NUMBER':'7402'},accounts(statuses))
    assert result['status']=='MULTIPLE_CANDIDATES'
    assert result['account_id'] is None
    assert result['method']=='EXACT_REGISTRATION_NUMBER'


def test_frames_without_status_keep_existing_registration_behavior():
    frame=accounts().drop(columns='STATUS')
    assert resolve_producer({'PRODUCER_NUMBER':'7402'},frame)['status']=='MULTIPLE_CANDIDATES'
    result=resolve_producer({'PRODUCER_NUMBER':'7402'},frame.iloc[:1])
    assert result['status']=='UNIQUE_MATCHED'
    assert result['method']=='EXACT_REGISTRATION_NUMBER'


@pytest.mark.parametrize('record,method',[
    ({'PRODUCER_NUMBER':'7402','PRODUCER_ACCOUNT_ID':'INACTIVE-ID'},'SOURCE_GUID'),
    ({'PRODUCER_NUMBER':'INACTIVE-ID'},'EXACT_ACCOUNT_ID'),
])
def test_guid_matches_are_unchanged_even_when_inactive(record,method):
    result=resolve_producer(record,accounts())
    assert result['status']=='UNIQUE_MATCHED'
    assert result['account_id']=='inactive-id'
    assert result['method']==method


def test_exact_account_id_collision_is_not_disambiguated_by_status():
    frame=accounts()
    frame.loc[0,'REGISTRATION_NUMBER']='inactive-id'
    result=resolve_producer({'PRODUCER_NUMBER':'inactive-id'},frame)
    assert result['status']=='MULTIPLE_CANDIDATES'
    assert result['method']=='EXACT_ACCOUNT_ID'
