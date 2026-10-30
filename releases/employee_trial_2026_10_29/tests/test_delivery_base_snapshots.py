"""Snapshot/closure arithmetic in a PENDING draft, never business writes."""
from copy import deepcopy
import pytest

from data.quota_position import quota_position, load_rules


def transaction(identity, kind, quantity, date, quota='q', **extra):
    return dict(QUOTA_TRANSACTION_ID=identity, QUOTA_ID=quota, OWNER_ACCOUNT_ID='owner',
                TRANSACTION_TYPE=kind, QUOTA_COUNT=quantity, EFFECTIVE_DATE=date, **extra)


def position(rows, *, pending=False, as_of='2026-10-30'):
    rules = load_rules()
    if not pending:
        rules['status'] = 'CONFIRMED'  # Synthetic gate exercise, not persisted approval.
    registrations = [dict(QUOTA_ID='q',ACCOUNT_ID='owner',QUOTA_TYPE='Non-Commercial Pullet'),
                     dict(QUOTA_ID='q2',ACCOUNT_ID='owner',QUOTA_TYPE='Non Commercial Pullet Quota')]
    return quota_position(registrations,rows,'owner','Non Commercial Pullet Quota',as_of,rules,
                          source_verified=True,missing_source_rows=0,inactive_source_rows=0)


def test_latest_base_absorbs_earlier_sale_and_base_without_double_deduction():
    rows=[transaction('b1','Base',5198,'2026-01-01'),
          transaction('s','Sale',400,'2026-02-01'),
          transaction('b2','Base',4798,'2026-03-01')]
    before=deepcopy(rows)
    result=position(rows)
    assert result['net_position']==4798 and result['components']['Base']==4798
    assert [r['QUOTA_TRANSACTION_ID'] for r in result['excluded_base_rows']]==['b1']
    assert [r['QUOTA_TRANSACTION_ID'] for r in result['absorbed_activity_rows']]==['s']
    assert rows==before
    assert position(rows,pending=True)['net_position'] is None
    assert load_rules()['status']=='PENDING' and load_rules()['flock_stock']['status']=='PENDING'


def test_latest_base_is_per_registration_and_asof_not_global():
    rows=[transaction('b1','Base',100,'2026-01-01'),
          transaction('b2','Base',80,'2026-03-01'),
          transaction('b3','Base',7,'2026-02-01',quota='q2'),
          transaction('future','Base',999,'2027-01-01'),
          transaction('ga','Global Adjustment',2,'2026-04-01')]
    assert position(rows)['net_position']==89
    assert position(rows,as_of='2026-01-31')['net_position']==100
    assert position(list(reversed(rows)))['net_position']==89


@pytest.mark.parametrize('extra', [transaction('tie','Base',100,'2026-01-01'),
                                 transaction('same-day','Sale',2,'2026-01-01')])
def test_same_day_ambiguity_never_picks_arbitrary_source_order(extra):
    result=position([transaction('b','Base',100,'2026-01-01'),extra])
    assert result['net_position'] is None
    assert any('same date' in r or 'share a date' in r for r in result['reasons'])


def test_termination_zero_effect_closes_without_changing_registration_or_inventing_balance():
    rows=[transaction('b','Base',100,'2026-01-01'),transaction('s','Sale',100,'2026-02-01'),
          transaction('closed','Terminate Quota',0,'2026-03-01')]
    result=position(rows)
    assert result['net_position']==0 and result['closed_registrations']==['q']
    assert result['components']['Terminate Quota']==0
    bad=position([rows[0],rows[2]])
    assert bad['net_position'] is None and any('non-zero' in r for r in bad['reasons'])


def test_closure_followed_by_activity_and_lease_crossing_snapshot_are_held():
    rows=[transaction('close','Terminate Quota',0,'2026-01-01'),transaction('base','Base',0,'2026-02-01')]
    assert position(rows)['net_position'] is None
    rows=[transaction('lease','Lease (In)',5,'2026-01-01',END_DATE='2026-12-31'),
          transaction('base','Base',100,'2026-02-01')]
    assert any('lease predates latest Base' in reason for reason in position(rows)['reasons'])


def test_unknown_snapshot_quantity_is_not_zero_or_replaced_by_old_base():
    rows=[transaction('old','Base',100,'2026-01-01'),transaction('new','Base',None,'2026-02-01')]
    result=position(rows)
    assert result['net_position'] is None and result['components']['Base'] is None
