"""Historical labels remain filterable/groupable; exports use the same result."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path

import pandas as pd
import pytest

from app.services.report_builder import build_report
from app.services.report_center import (build_custom_report, report_csv, report_xlsx,
                                        transaction_type_options)
from tests.auth_support import authenticated_app
from tests.test_report_center import user
from tests.test_staff_workflows import chain


CASES = {
    'Purchase': ([Decimal('1.1250'), Decimal('0.8750')], Decimal(2)),
    'Lease (In)': ([Decimal('5.0001'), Decimal('2.0001')], Decimal('7.0002')),
    'Lease (Out)': ([Decimal('1.1000'), Decimal('0.1250')], Decimal('1.225')),
    'Base': ([None, None], None),
    'Adjustment': ([Decimal('-3.1250'), Decimal('1.0000')], Decimal('-2.125')),
    'Global Adjustment': ([Decimal(0), None], Decimal(0)),
    'Terminate Quota': ([Decimal(0), Decimal(0)], Decimal(0)),
}


@pytest.fixture
def history(chain):
    repo, account, other, facility, quota, flock, _ = chain
    rows = []
    for kind, (values, expected) in CASES.items():
        for value in values:
            rows.append(dict(QUOTA_TRANSACTION_ID=f'synthetic-history-{len(rows)}', QUOTA_ID=quota,
                             OWNER_ACCOUNT_ID=account, TRANSACTION_TYPE=kind, QUOTA_COUNT=value,
                             EFFECTIVE_DATE='2026-01-01', QUOTA_LEASE_TYPE='Non One Time Credit', PRICE=None))
    repo._quota_transactions = pd.concat([repo._quota_transactions, pd.DataFrame(rows)], ignore_index=True)
    rows = [dict(FLOCK_TRANSACTION_ID=f'synthetic-ft-{i}', FLOCK_ID=flock,
                 TRANSACTION_TYPE=kind, QUANTITY=qty, TRANSACTION_DATE='2026-01-01')
            for i, (kind, qty) in enumerate([('Count', 10), ('Count', 11),
                ('DEV_TEST historical observation', 5), ('DEV_TEST historical observation', 7)])]
    repo._flock_transactions = pd.concat([repo._flock_transactions, pd.DataFrame(rows)], ignore_index=True)
    return repo


def assert_exports_equal(frame):
    for exported in (pd.read_csv(BytesIO(report_csv(user(), frame))),
                     pd.read_excel(BytesIO(report_xlsx(user(), frame)))):
        assert list(exported.columns) == list(frame.columns) and len(exported) == len(frame)
        for column in frame:
            for expected, actual in zip(frame[column], exported[column]):
                if pd.isna(expected):
                    assert pd.isna(actual)
                elif isinstance(expected, Decimal):
                    # Compare exact decimal value, not Decimal vs binary float.
                    assert Decimal(str(actual)) == expected
                else:
                    assert actual == expected


@pytest.mark.parametrize('kind', list(CASES))
def test_quota_historical_filter_group_and_exports(history, kind):
    result = build_custom_report(history, user=user(), dataset='Quota Transactions',
        selected_fields=['TRANSACTION_TYPE', 'QUOTA_LEASE_TYPE', 'QUOTA_COUNT'],
        filters={'transaction_type': kind}, group_by=['TRANSACTION_TYPE', 'QUOTA_LEASE_TYPE'],
        aggregations={'QUOTA_COUNT': 'sum'})
    assert list(result.columns) == ['Transaction Type', 'Credit Type', 'Quota Count']
    assert len(result) == 1 and result.iloc[0]['Transaction Type'] == kind
    actual = result.iloc[0]['Quota Count']
    expected = CASES[kind][1]
    assert pd.isna(actual) if expected is None else actual == expected
    assert result.iloc[0]['Credit Type'] == 'Non One Time Credit'
    assert_exports_equal(result)


def test_legacy_builder_keeps_all_types_and_credit_label(history):
    # This older API selects joined fields; it does not itself accept filters
    # or grouping, and has no Flock Transaction dataset. Do not invent one.
    result = build_report(history, ['QUOTA_TRANSACTION_ID', 'QUOTA_TRANSACTION_TYPE',
                                    'QUOTA_LEASE_TYPE', 'QUOTA_COUNT'])
    assert set(result['Quota Transaction Type']) == set(CASES)
    assert 'Credit Type' in result and 'Quota Lease Type' not in result
    assert len(result) == sum(len(values) for values, _ in CASES.values())
    assert_exports_equal(result)


def test_nonconstant_flock_type_filter_group_export(history):
    kind = 'DEV_TEST historical observation'
    assert kind in transaction_type_options(history, 'Flock Transactions')
    result = build_custom_report(history, user=user(), dataset='Flock Transactions',
        selected_fields=['TRANSACTION_TYPE', 'QUANTITY'], filters={'transaction_type': kind},
        group_by=['TRANSACTION_TYPE'], aggregations={'QUANTITY': 'sum'})
    assert len(result) == 1 and result.iloc[0]['Quantity'] == 12
    assert_exports_equal(result)


def test_actual_customize_page_historical_filter_group_and_exports(history, tmp_path, monkeypatch):
    app = authenticated_app(Path(__file__).resolve().parents[1] / 'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = history
    app.switch_page('app/pages/4_Reports.py').run()
    app.radio(key='report_center_section').set_value('Customize Report').run()
    app.selectbox(key='custom_report_dataset').set_value('Quota Transactions').run()
    assert not app.exception and not app.error, [e.value for e in app.error]
    assert set(CASES).issubset(app.selectbox(key='custom_filter_transaction').options)
    assert 'Credit Type' in app.multiselect(key='custom_report_columns').options
    app.multiselect(key='custom_report_columns').set_value(['Transaction Type', 'Credit Type', 'Quota Count']).run()
    app.selectbox(key='custom_filter_transaction').set_value('Lease (In)')
    app.multiselect(key='custom_report_group').set_value(['Transaction Type', 'Credit Type']).run()
    assert app.multiselect(key='custom_report_group').value == ['Transaction Type', 'Credit Type']
    app.selectbox(key='custom_report_aggregate_field').set_value('Quota Count').run()
    app.selectbox(key='custom_report_aggregate').set_value('sum')
    next(b for b in app.button if b.label == 'Run Report').click().run()
    assert not app.exception and not app.error, [e.value for e in app.error]
    result = app.session_state.custom_report_result
    assert len(result) == 1 and result.iloc[0]['Quota Count'] == Decimal('7.0002')
    assert any(frame.value.equals(result) for frame in app.dataframe)
    assert_exports_equal(result)
    # Changing dataset clears the old quota-only filter, instead of ignoring it.
    app.selectbox(key='custom_report_dataset').set_value('Flock Transactions').run()
    assert not app.exception and app.selectbox(key='custom_filter_transaction').value == 'All'
    app.selectbox(key='custom_filter_transaction').set_value('DEV_TEST historical observation')
    app.multiselect(key='custom_report_columns').set_value(['Transaction Type', 'Quantity']).run()
    app.multiselect(key='custom_report_group').set_value(['Transaction Type']).run()
    app.selectbox(key='custom_report_aggregate_field').set_value('Quantity').run()
    app.selectbox(key='custom_report_aggregate').set_value('sum')
    next(b for b in app.button if b.label == 'Run Report').click().run()
    assert not app.exception and not app.error
    result = app.session_state.custom_report_result
    assert result.iloc[0]['Quantity'] == 12
    assert_exports_equal(result)
