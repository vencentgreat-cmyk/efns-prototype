"""Additional offline save boundaries; fake SQL capture is NOT engine evidence."""
from decimal import Decimal

import pandas as pd
import pytest

from data.connection import _literalize_null_bindings
from data.constants import QUOTA_TRANSACTION_TYPES, UNASSIGNED_LABEL
from data.repositories.snowflake import SnowflakeRepository
from data.validation import parse_optional_quota_price
from tests.test_daily_quota_entry import quota_app
from tests.test_staff_workflows import chain


@pytest.mark.parametrize('entered,expected', [('', None), ('0', Decimal(0))])
def test_native_writer_keeps_null_and_zero_distinct_in_parameter_bindings(entered, expected):
    class Capture:
        def __init__(self):
            self.calls = []

        def execute(self, sql, params=None):
            self.calls.append((sql, params))
            return 1

    capture = Capture()
    price = parse_optional_quota_price(entered)
    repo = SnowflakeRepository()
    repo._upsert_with_executor(capture, 'QUOTA_TRANSACTION', dict(
        QUOTA_ID='synthetic-quota', OWNER_ACCOUNT_ID='synthetic-owner',
        TRANSACTION_TYPE='Purchase', EFFECTIVE_DATE='2026-01-01',
        QUOTA_COUNT=Decimal('2.1250'), PRICE=price))
    assert len(capture.calls) == 1
    sql, parameters = capture.calls[0]
    columns = [c.strip() for c in sql.split('(', 1)[1].split(')', 1)[0].split(',')]
    bound = dict(zip(columns, parameters))
    assert bound['PRICE'] is None if expected is None else bound['PRICE'] == expected
    assert bound['QUOTA_COUNT'] == Decimal('2.1250')
    statement, bindings = _literalize_null_bindings('VALUES (?, ?)', (price, Decimal(0)))
    if expected is None:
        assert statement == 'VALUES (NULL, ?)' and bindings == [Decimal(0)]
    else:
        assert statement == 'VALUES (?, ?)' and bindings == [Decimal(0), Decimal(0)]


def test_invalid_price_blocks_save_without_erasing_form(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, _ = chain
    app = quota_app(repo, tmp_path, monkeypatch)
    assert app.selectbox(key='quota_tx_form_type').options == list(QUOTA_TRANSACTION_TYPES)
    related = next(v for v in app.selectbox(key='quota_tx_form_related_account').options if 'counterparty' in v)
    app.selectbox(key='quota_tx_form_related_account').select(related)
    app.number_input(key='quota_tx_form_count').set_value(2.5)
    app.text_area(key='quota_tx_form_comments').input('Synthetic retained draft')
    app.text_input(key='quota_tx_form_price').input('not numeric')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and any('Price must be' in e.value for e in app.error)
    assert repo.get_quota_transactions().empty and repo.get_record_revisions().empty
    assert app.text_input(key='quota_tx_form_price').value == 'not numeric'
    assert app.text_area(key='quota_tx_form_comments').value == 'Synthetic retained draft'


def test_price_null_retry_after_navigation_failure_has_one_create_history(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, _ = chain
    app = quota_app(repo, tmp_path, monkeypatch)
    related = next(v for v in app.selectbox(key='quota_tx_form_related_account').options if 'counterparty' in v)
    app.selectbox(key='quota_tx_form_related_account').select(related)
    app.number_input(key='quota_tx_form_count').set_value(2)
    from app import navigation

    def interrupted(*args, **kwargs):
        raise RuntimeError('Synthetic navigation interruption after save')

    monkeypatch.setattr(navigation, 'open_view', interrupted)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    rows = repo.get_quota_transactions()
    assert len(rows) == 1 and pd.isna(rows.iloc[0].PRICE)
    assert len(repo.get_record_revisions()) == 1
    assert len(repo._migration_review_audit) == 1


def test_required_counterparty_cannot_be_explicitly_cleared_on_edit(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, _ = chain
    target = repo.upsert_quota_transaction(dict(QUOTA_ID=quota, TRANSACTION_TYPE='Purchase',
        QUOTA_COUNT=2, EFFECTIVE_DATE='2026-01-01', RELATED_ACCOUNT_ID=other, PRICE=None))
    before = repo._quota_transactions.copy(deep=True)
    app = quota_app(repo, tmp_path, monkeypatch, 'edit', target)
    app.selectbox(key='quota_tx_form_related_account').select(UNASSIGNED_LABEL)
    app.text_input(key='quota_tx_form_revision_reason').input('Synthetic attempted clear')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and any('Related Account is required' in e.value for e in app.error)
    pd.testing.assert_frame_equal(repo._quota_transactions, before)
    assert repo.get_record_revisions().empty
