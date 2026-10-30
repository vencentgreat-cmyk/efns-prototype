"""Synthetic review gates; no company connection or real business fixtures."""
from copy import deepcopy
from decimal import Decimal

import pandas as pd
import pytest

from app.services.quota_usage import account_usage_context, usage_numbers
from data.flock_stock import flock_stock
from data.quota_position import quota_position, load_rules, component_table
from data.migration import normalize_migration_row, load_new_package_mapping
from tests.test_staff_workflows import chain


def regs():
    return pd.DataFrame([{'QUOTA_ID': 'q', 'ACCOUNT_ID': 'owner', 'QUOTA_TYPE': 'Egg'}])


def tx(kind='Base', qty=100, **changes):
    return dict(QUOTA_TRANSACTION_ID='t', QUOTA_ID='q', OWNER_ACCOUNT_ID='owner',
                RELATED_ACCOUNT_ID='other', TRANSACTION_TYPE=kind, QUOTA_COUNT=qty,
                EFFECTIVE_DATE='2026-01-01', END_DATE='2026-12-31', **changes)


def confirmed():
    rules = load_rules()
    rules['status'] = 'CONFIRMED'
    rules['terminate_policy'] = 'IGNORE_ZERO'
    rules['flock_stock'].update(status='CONFIRMED', lifecycle_rule='EXPLICIT_SCOPE')
    return rules


def position(rows, rules=None, **kwargs):
    evidence = dict(source_verified=True, missing_source_rows=0, inactive_source_rows=0)
    evidence.update(kwargs)
    return quota_position(regs(), pd.DataFrame(rows), 'OWNER', 'Egg', '2026-06-15',
                          rules or confirmed(), **evidence)


def test_pending_never_becomes_capacity_or_percentage():
    p = position([tx()], load_rules())
    assert p['net_position'] is None and 'Quota rules UNCONFIRMED' in p['reasons']
    assert usage_numbers(10, 0, p['net_position'], compatible_units=True)['usage_percent'] is None
    assert load_rules()['flock_stock']['status'] == 'PENDING'


def test_confirmed_components_owner_only_and_signed_adjustment():
    rows = [tx(), dict(tx('Purchase', 20), QUOTA_TRANSACTION_ID='buy'),
            dict(tx('Sale', 10), QUOTA_TRANSACTION_ID='sell'),
            dict(tx('Adjustment', -4), QUOTA_TRANSACTION_ID='adj'),
            dict(tx('Sale', 20), QUOTA_TRANSACTION_ID='counterparty', QUOTA_ID='other-q',
                 OWNER_ACCOUNT_ID='other', RELATED_ACCOUNT_ID='owner')]
    p = position(rows)
    assert p['net_position'] == 106 and not p['reasons']
    assert p['components']['Adjustment'] == -4


@pytest.mark.parametrize('date,expected', [('2026-01-01', 7), ('2026-12-31', 7), ('2027-01-01', 0), ('2025-12-31', 0)])
def test_inclusive_lease_range(date, expected):
    result = quota_position(regs(), pd.DataFrame([tx('Lease (In)', 7)]), 'owner', 'Egg', date,
                            confirmed(), source_verified=True, missing_source_rows=0, inactive_source_rows=0)
    assert result['net_position'] == expected


@pytest.mark.parametrize('changes,reason', [
    ({'missing_source_rows': 3}, '3 source rows not in CORE'),
    ({'pending_rejected_count': 2}, '2 pending/rejected source rows'),
    ({'inactive_source_rows': 1}, '1 Inactive source transactions excluded'),
    ({'source_verified': False}, 'RAW completeness'),
    ({'missing_source_rows': None}, 'RAW completeness')])
def test_source_gaps_block_even_with_confirmed_rules(changes, reason):
    result = position([tx()], **changes)
    assert result['net_position'] is None and any(reason in r for r in result['reasons'])


def test_unattributed_gaps_are_not_reassigned_to_a_counterparty():
    p = position([tx()], unresolved_owner_rows=2)
    assert p['net_position'] is None and any('unresolved Owner' in reason for reason in p['reasons'])


def test_orphan_registration_does_not_silently_vanish():
    p = position([dict(tx(), QUOTA_ID='missing')])
    assert p['net_position'] is None and any('missing Registration' in reason for reason in p['reasons'])


def test_lease_out_and_expired_or_future_activity():
    rows = [tx(), dict(tx('Lease (Out)', 7), QUOTA_TRANSACTION_ID='out'),
            dict(tx('Lease (In)', 4), QUOTA_TRANSACTION_ID='in'),
            dict(tx('Purchase', 500), QUOTA_TRANSACTION_ID='future', EFFECTIVE_DATE='2027-01-01')]
    assert position(rows)['net_position'] == 97


@pytest.mark.parametrize('row,reason', [
    (tx('Unrecognized'), 'unknown transaction'),
    (tx(RAW_STATECODE='Inactive'), 'Inactive'),
    (tx(STATECODE=1), 'Inactive'),
    (dict(tx(), QUOTA_COUNT=float('nan')), 'Missing/invalid Quota Count'),
    (dict(tx('Lease (Out)'), END_DATE=None), 'End Date'),
    (dict(tx(), OWNER_ACCOUNT_ID='other'), 'Owner conflicts'),
    (tx('Sale', -1), 'Negative quantity')])
def test_bad_or_inactive_input_blocks(row, reason):
    p = position([row])
    assert p['net_position'] is None and any(reason in s for s in p['reasons'])


def test_duplicate_identity_blocks_instead_of_offsetting_missing_rows():
    assert position([tx(), tx()])['net_position'] is None
    duplicate = pd.concat([regs(), regs()], ignore_index=True)
    p = quota_position(duplicate, pd.DataFrame([tx()]), 'owner', 'Egg', '2026-06-15', confirmed())
    assert 'Registration identity missing or duplicate' in p['reasons']


@pytest.mark.parametrize('kind', ['National Allocation', 'Provincial Allocation'])
def test_allocation_is_never_entitlement_or_importable(kind):
    p = position([tx(), dict(tx(kind, 746357), QUOTA_TRANSACTION_ID='national')])
    assert p['net_position'] == 100 and p['excluded_allocation_count'] == 1
    mapping = load_new_package_mapping()
    raw = {'NEW_QUOTATRANSACTIONSID': 'synthetic', 'NEW_QUOTATRANSACTIONTYPE_DISPLAYNAME': kind}
    record, errors = normalize_migration_row('QUOTA_TRANSACTION', raw, 2, mapping)
    assert record['TRANSACTION_TYPE'] == kind
    assert any('never import' in s for s in errors)


def test_initial_flag_is_not_a_direction_and_null_zero_are_distinct():
    assert position([tx(EFC_TRANSACTIONINITIALFLAG='No', NEW_RESERVEQUOTA=0)])['net_position'] == 100
    assert position([tx(EFC_TRANSACTIONINITIALFLAG='Yes', NEW_RESERVEQUOTA=None)])['net_position'] == 100
    table = component_table(pd.DataFrame([dict(tx(qty=None), QUOTA_TRANSACTION_ID='a'),
                                        dict(tx(qty=0), QUOTA_TRANSACTION_ID='b')]))
    assert table.iloc[0]['Recorded quantity'] == 0 and table.iloc[0]['Missing quantities'] == 1
    assert component_table(pd.DataFrame([tx(qty=None)])).iloc[0]['Recorded quantity'] is None


def ftx(kind='Count', qty=10, date='2026-06-01', source='Producer', ident='ft'):
    return dict(FLOCK_TRANSACTION_ID=ident, FLOCK_ID='f', TRANSACTION_TYPE=kind,
                TRANSACTION_DATE=date, QUANTITY=qty, COUNT_SOURCE_LABEL=source)


def stock(rows, rules=None, **kwargs):
    evidence = dict(source_verified=True, missing_source_rows=0, inactive_source_rows=0, live_scope=True)
    evidence.update(kwargs)
    return flock_stock({'FLOCK_ID': 'F', 'BIRD_COUNT': 12, 'STATUS': 'Active', 'NEW_NETBIRDCOUNT': 10},
                       pd.DataFrame(rows), '2026-06-15', rules or confirmed(), **evidence)


def test_counts_are_observations_type_only_deltas_and_reference_is_not_formula():
    result = stock([ftx(), ftx('Delivery', 5, '2026-06-02', ident='in'),
                    ftx('Removal', 2, '2026-06-03', ident='out'),
                    ftx('Sale', 1, '2026-06-04', ident='sale')])
    assert result['candidate_current_stock'] == 12
    assert result['old_system_reference'] == 10 and result['bird_count'] == 12
    assert stock([ftx(qty=0)])['candidate_current_stock'] == 0
    assert stock([ftx()], load_rules())['candidate_current_stock'] is None


@pytest.mark.parametrize('rows,reason', [
    ([ftx(), ftx(source='Board', ident='b')], 'Same-day Count'),
    ([ftx(), ftx(qty=11, ident='b')], 'Same-day Count'),
    ([ftx(), dict(ftx(ident='inactive'), RAW_STATECODE='Inactive')], 'Inactive'),
    ([ftx(date=None)], 'date missing'),
    ([ftx(qty=float('nan'))], 'No usable'),
    ([ftx(), ftx('Delivery', 2, ident='in')], 'share a date'),
    ([ftx(), ftx('Removal', 20, '2026-06-02', ident='out')], 'negative')])
def test_stock_conflicts_not_auto_picked(rows, reason):
    result = stock(rows)
    assert result['candidate_current_stock'] is None
    assert any(reason in r for r in result['reasons'])


def test_scope_not_status_does_not_end_or_clear_flock():
    assert stock([ftx()], live_scope=None)['candidate_current_stock'] is None
    assert stock([ftx()], inactive_source_rows=1)['candidate_current_stock'] is None
    f = {'FLOCK_ID': 'f', 'STATUS': 'Inactive', 'BIRD_COUNT': 12, 'DISPOSAL_DATE': '2020-01-01'}
    before = deepcopy(f)
    result = flock_stock(f, [ftx()], '2026-06-15', load_rules())
    assert f == before and result['candidate_current_stock'] is None


def test_usage_remains_blocked_without_source_stock_and_units(chain):
    repo, account, *_ = chain
    result = account_usage_context(repo, account, rules=confirmed())
    assert all(row['usage_percent'] is None for row in result['summaries'])
    assert all(row['position']['net_position'] is None for row in result['summaries'])
