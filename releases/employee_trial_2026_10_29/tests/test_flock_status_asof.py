"""Confirmed as-of fixes, with synthetic edge cases and frozen current output."""
from decimal import Decimal
import hashlib

import pandas as pd
import pytest

from app.services.flock_current_report import build_flock_current_report, latest_observation
from app.services.flock_age_report import utilization
from app.services.flock_reports import build_flock_status_report, build_flock_status_by_producer_report
from tests.test_flock_current_report import sources

AS_OF = '2026-06-19'
FALLBACKS = [
    ('40397','7050',15674), ('40404','7078',28800), ('40399','7101',51300),
    ('40396','7107',39772), ('40406','7113',10700), ('40405','7168',36000),
    ('40400','7172',35568), ('40401','7172',25704), ('40403','7173',80640),
    ('40398','7178',24712),
]


def example(permit='40378', quantity=39552, placement='2026-04-16', hatch='2025-12-04'):
    f,t,a=sources([(permit,hatch,placement,'2026-06-12',quantity,0,0,0)])
    f['BIRD_COUNT']=quantity;f['FACILITY_ID']='facility'
    a['REGISTRATION_NUMBER']='7169';a['PRODUCER_ROLE']=True
    return f,t,a


def status(f,t,a,quotas=None,as_of=AS_OF):
    return build_flock_status_report(f,t,a,pd.DataFrame(),quotas or {'bayview':72816},as_of)


@pytest.mark.parametrize('other_source',[None,'','   ','Board'])
@pytest.mark.parametrize('reverse',[False,True])
def test_40378_same_quantity_different_source_is_usable(other_source,reverse):
    f,t,a=example();t['COUNT_SOURCE_LABEL']='Producer'
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],COUNT_SOURCE_LABEL=other_source)])],ignore_index=True)
    if reverse:t=t.iloc[::-1]
    _,selected,counted,note=latest_observation(t.to_dict('records'))
    assert selected['COUNT_SOURCE_LABEL'] and counted==39552 and note==''
    if other_source in (None,'','   '):assert selected['COUNT_SOURCE_LABEL']=='Producer'
    frame,summary=status(f,t,a)
    detail=frame.loc[frame['Permit No']=='40378'].iloc[0]
    assert detail.Inventory==39515 and detail['Util.']=='54.27%'
    assert summary['Inventory Birds']==39515


def test_different_usable_quantities_still_conflict_and_count_wins_delivery_tie():
    f,t,a=example()
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],TRANSACTION_TYPE='Delivery',QUANTITY=1)])])
    assert status(f,t,a)[0].iloc[1].Inventory==39515
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],QUANTITY=39553,COUNT_SOURCE_LABEL=None)])])
    row=build_flock_current_report(f,t,a,AS_OF).iloc[0]
    assert row.Counted==row.Inventory=='—' and row.Notes=='Count conflict'


@pytest.mark.parametrize('invalid',[None,-1,Decimal('1.5')])
@pytest.mark.parametrize('mixed',[False,True])
def test_invalid_quantities_never_become_a_usable_count(invalid,mixed):
    f,t,a=example();bad=dict(t.iloc[0],QUANTITY=invalid,COUNT_SOURCE_LABEL=None)
    t=pd.concat([t,pd.DataFrame([bad])]) if mixed else pd.DataFrame([bad])
    row=build_flock_current_report(f,t,a,AS_OF).iloc[0]
    assert row.Counted==row.Inventory=='—' and row.Notes=='Invalid Count quantity'


@pytest.mark.parametrize('permit,registration,birds',FALLBACKS)
def test_confirmed_upcoming_bird_count_fallbacks(permit,registration,birds):
    f,t,a=example(permit,birds,placement='2026-12-01',hatch='2026-08-01')
    a['REGISTRATION_NUMBER']=registration
    t['TRANSACTION_DATE']='2026-08-01'  # Future row must not be used as an as-of Count.
    t['QUANTITY']=birds+100
    frame,summary=status(f,t,a)
    detail=frame.loc[frame['Permit No']==permit].iloc[0]
    assert detail.Inventory==0 and detail['Up. Flocks']==birds and detail['Util.']=='0.00%'
    assert frame.iloc[0]['Up. Flocks']==birds and frame.iloc[0].Inventory==0
    assert summary['Inventory Birds']==0
    current=build_flock_current_report(f,t,a,AS_OF)
    assert current.iloc[0]['Count Date']==current.iloc[0].Counted=='—'
    assert 'Stored Bird Count used' in current.iloc[0].Notes


@pytest.mark.parametrize('hatch',[None,'2026-01-01','2026-06-19','2026-08-01'])
def test_future_placement_is_not_excluded_by_hatch_date(hatch):
    f,t,a=example(placement='2026-12-01',hatch=hatch)
    row=status(f,t.iloc[:0],a)[0].iloc[1]
    assert row.Inventory==0 and row['Up. Flocks']==39552 and row['Util.']=='0.00%'


def test_earlier_observation_still_wins_stored_bird_count_for_40382():
    # Dates/quantity here are synthetic to distinguish the observation from BIRD_COUNT.
    f,t,a=example('40382',6800,placement='2026-06-23',hatch='2026-02-10')
    f['BIRD_COUNT']=6840
    row=status(f,t,a)[0].iloc[1]
    assert row.Inventory==0 and row['Up. Flocks']==6800
    f['PLACEMENT_DATE']='2026-06-18'
    row=status(f,t,a)[0].iloc[1]
    assert row.Inventory==6793 and row['Up. Flocks']==0


def test_existing_conflict_is_not_replaced_by_upcoming_bird_count():
    f,t,a=example(placement='2026-12-01')
    t=pd.concat([t,pd.DataFrame([dict(t.iloc[0],QUANTITY=1)])])
    row=build_flock_current_report(f,t,a,AS_OF).iloc[0]
    assert row.Inventory==row['Up. Flocks']=='—' and row.Notes=='Count conflict'


@pytest.mark.parametrize('birds',[None,-1,Decimal('1.5')])
def test_invalid_upcoming_bird_count_is_flagged_not_invented(birds):
    f,t,a=example(placement='2026-12-01');f['BIRD_COUNT']=birds
    row=build_flock_current_report(f,t.iloc[:0],a,AS_OF).iloc[0]
    assert row.Inventory==0 and row['Up. Flocks']=='—'
    assert 'Invalid stored Bird Count' in row.Notes


def test_all_fallback_contributions_sum_per_producer_without_mutation():
    flocks=[];accounts=[]
    for permit,owner,birds in FALLBACKS:
        f,_,a=example(permit,birds,placement='2026-12-01',hatch='2026-08-01')
        flocks.append(f.assign(ACCOUNT_ID=owner))
        accounts.append(a.assign(ACCOUNT_ID=owner,REGISTRATION_NUMBER=owner,ORGANIZATION_NAME=owner))
    f=pd.concat(flocks,ignore_index=True);a=pd.concat(accounts,ignore_index=True).drop_duplicates('ACCOUNT_ID')
    _,t,_=example();t=t.iloc[:0];before=f.copy(deep=True)
    result,summary=status(f,t,a,{owner:100000 for owner in a.ACCOUNT_ID})
    totals=result.loc[result['Permit No']=='Total'].set_index('Reg No')
    assert totals['Up. Flocks'].to_dict()=={'7050':15674,'7078':28800,'7101':51300,'7107':39772,
        '7113':10700,'7168':36000,'7172':61272,'7173':80640,'7178':24712}
    assert totals.Inventory.eq(0).all() and summary['Inventory Birds']==0
    pd.testing.assert_frame_equal(f,before)


@pytest.mark.parametrize('registration',['pr.12345regis',' PR.12345REGIS '])
def test_exact_test_account_excluded_from_rows_and_all_status_totals(registration):
    f,t,a=example();expected,expected_summary=status(f,t,a)
    test_flocks=pd.concat([f.assign(FLOCK_ID='test-1',ACCOUNT_ID='test',PERMIT_NUMBER='pr-11.13demotest'),
                          f.assign(FLOCK_ID='test-2',ACCOUNT_ID='test',PERMIT_NUMBER='flockdev-23')])
    test_account=a.assign(ACCOUNT_ID='test',REGISTRATION_NUMBER=registration)
    combined_f=pd.concat([f,test_flocks]);combined_a=pd.concat([a,test_account]);before=combined_f.copy(deep=True)
    combined_t=pd.concat([t,t.assign(FLOCK_ID='test-1'),t.assign(FLOCK_ID='test-2')])
    actual,summary=status(combined_f,combined_t,combined_a,{'bayview':72816,'test':999999})
    pd.testing.assert_frame_equal(actual,expected);assert summary==expected_summary
    selected,own=build_flock_status_by_producer_report(combined_f,combined_t,combined_a,pd.DataFrame(),
        {'bayview':72816,'test':999999},AS_OF,'bayview')
    pd.testing.assert_frame_equal(selected,expected);assert own['NFPMC Allocation']==72816
    removed,removed_summary=build_flock_status_by_producer_report(combined_f,combined_t,combined_a,
        pd.DataFrame(),{'bayview':72816,'test':999999},AS_OF,'test')
    assert removed.empty and removed_summary is None
    pd.testing.assert_frame_equal(combined_f,before)


def test_other_pr_registration_and_flock_names_are_not_broadly_excluded():
    f,t,a=example('flockdev-23');a['REGISTRATION_NUMBER']='pr.real-producer'
    result,summary=status(f,t,a)
    assert not result.empty and summary['Inventory Birds']==39515


def test_producers_over_quota_excludes_only_test_account_and_preserves_real_totals():
    from app.services.producers_over_quota_report import build_producers_over_quota_report
    f,t,a=example()
    expected,expected_summary=build_producers_over_quota_report(f,t,a,pd.DataFrame(),{'bayview':72816},AS_OF)
    combined_f=pd.concat([f,f.assign(FLOCK_ID='test',ACCOUNT_ID='test',PERMIT_NUMBER='flockdev-23')])
    combined_t=pd.concat([t,t.assign(FLOCK_ID='test')])
    combined_a=pd.concat([a,a.assign(ACCOUNT_ID='test',REGISTRATION_NUMBER='pr.12345regis')])
    before=combined_f.copy(deep=True)
    result,summary=build_producers_over_quota_report(combined_f,combined_t,combined_a,pd.DataFrame(),
        {'bayview':72816,'test':999999},AS_OF)
    pd.testing.assert_frame_equal(result,expected)
    assert result.attrs==expected.attrs and summary==expected_summary
    pd.testing.assert_frame_equal(combined_f,before)
    a['REGISTRATION_NUMBER']='pr.real-producer'
    result,summary=build_producers_over_quota_report(f,t,a,pd.DataFrame(),{'bayview':72816},AS_OF)
    assert not result.empty and summary['Inventory Birds']==39515


def test_current_date_observation_backed_status_is_identical_to_pre_fix_baseline():
    f,t,a=sources();f['FACILITY_ID']='facility'
    result,summary=build_flock_status_report(f,t,a,pd.DataFrame([dict(FACILITY_ID='facility',
        FACILITY_NAME='Synthetic barn')]),{'bayview':77862},'2026-11-13')
    # Frozen from main before this fix, across every displayed cell and column.
    assert hashlib.sha256(result.to_csv(index=False).replace('\r\n','\n').encode('utf8')).hexdigest()==(
        '7cbdbb81f71001fd5a69074c9116f0ddd08b7192adab54ab409aa1f729e63ce3')
    assert [(r['Permit No'],r['Inventory'],r['Up. Flocks'],r['Flock Age'],r['Util.']) for r in result.to_dict('records')]==[
        ('Total',69785,11000,'—','89.63%'),('30369',1854,0,68,'2.38%'),
        ('40368',9819,0,63,'12.61%'),('40382',6724,0,39,'8.64%'),
        ('40390',12370,0,27,'15.89%'),('40396',39018,0,20,'50.11%'),('40407',0,11000,9,'0.00%')]
    assert summary=={'Inventory Birds':69785,'NFPMC Allocation':Decimal(77862),
        'Provincial Utilization':'89.63%','Issuance for Province':Decimal(77862),'Producers with Quota':0,
        'Notes':'0 Account quota(s) unavailable; 0 flock Inventory value(s) excluded'}


def test_supplied_7169_acceptance_percentage_formats_as_legacy():
    # These are supplied acceptance totals, not fabricated underlying flock rows.
    assert utilization(87743,72816)=='120.50%'
