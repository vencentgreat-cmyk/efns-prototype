"""Daily entry fidelity, using isolated Mock state and actual local pages."""
from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from data.constants import QUOTA_TRANSACTION_TYPES, QUOTA_TRANSACTION_INPUT_TYPES
from data.validation import (parse_optional_quota_price, quota_related_account_required,
                             validate_quota_transaction)
from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain


@pytest.mark.parametrize('kind,required', [
    ('Purchase', True), ('Sale', True), ('Lease (In)', True), ('Lease (Out)', True),
    ('Lease In', True), ('Lease Out', True), ('Base', False), ('Adjustment', False),
    ('Global Adjustment', False), ('Terminate Quota', False)])
def test_related_account_provisional_rule_without_broadening_new_choices(chain, kind, required):
    repo, account, other, facility, quota, flock, _ = chain
    record = dict(QUOTA_ID=quota, TRANSACTION_TYPE=kind, QUOTA_COUNT=2,
                  EFFECTIVE_DATE='2026-01-01', RELATED_ACCOUNT_ID=None)
    errors = validate_quota_transaction(repo, record)
    assert quota_related_account_required(kind) is required
    assert any('Related Account is required' in e for e in errors) is required
    record['RELATED_ACCOUNT_ID'] = other
    assert not any('Related Account' in e for e in validate_quota_transaction(repo, record))
    record['RELATED_ACCOUNT_ID'] = 'synthetic-missing'
    assert 'Related Account does not exist.' in validate_quota_transaction(repo, record)
    # This task changes the counterparty rule, NOT the daily type allowlist.
    assert ('Transaction Type is required.' in errors) is (kind not in QUOTA_TRANSACTION_INPUT_TYPES)


@pytest.mark.parametrize('raw,expected', [(None, None), ('', None), ('  ', None),
                                       ('0', Decimal(0)), ('12.50', Decimal('12.50'))])
def test_optional_price_parser(raw, expected):
    assert parse_optional_quota_price(raw) == expected


@pytest.mark.parametrize('raw', ['NaN', 'Infinity', '-1', 'not a price', True])
def test_invalid_price_is_rejected(raw):
    with pytest.raises(ValueError, match='Price must be'):
        parse_optional_quota_price(raw)


def quota_app(repo, tmp_path, monkeypatch, view='new', identity=None):
    app = authenticated_app(Path(__file__).resolve().parents[1] / 'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repo
    app.session_state['_efns_record_8_Quota_Transactions_view'] = view
    if identity:
        app.session_state['_efns_record_8_Quota_Transactions_id'] = identity
    return app.switch_page('app/pages/8_Quota_Transactions.py').run()


@pytest.mark.parametrize('entered,expected', [('', None), ('0', Decimal(0))])
def test_price_create_and_comment_edit_preserve_unknown_vs_zero(chain, tmp_path, monkeypatch, entered, expected):
    repo, account, other, facility, quota, flock, _ = chain
    app = quota_app(repo, tmp_path, monkeypatch)
    assert not app.exception
    assert app.text_input(key='quota_tx_form_price').value == ''
    app.selectbox(key='quota_tx_form_type').select('Purchase').run()
    assert app.selectbox(key='quota_tx_form_related_account').label == 'Related Account *'
    label = next(v for v in app.selectbox(key='quota_tx_form_related_account').options
                 if 'counterparty' in v)
    app.selectbox(key='quota_tx_form_related_account').select(label)
    app.number_input(key='quota_tx_form_count').set_value(2.125)
    app.text_input(key='quota_tx_form_price').input(entered)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    rows = repo.get_quota_transactions()
    assert len(rows) == 1
    target = rows.iloc[0].QUOTA_TRANSACTION_ID
    stored = repo.get_quota_transaction(target)
    assert pd.isna(stored['PRICE']) if expected is None else stored['PRICE'] == expected
    assert any('2.125' in m.value for m in app.markdown)
    assert any(('—' if expected is None else '$0.00') in m.value for m in app.markdown if '**Price**' in m.value)
    app.button(key='quota_tx_record_edit').click().run()
    assert not app.exception
    app.text_area(key='quota_tx_form_comments').input('Synthetic notes-only edit')
    app.text_input(key='quota_tx_form_revision_reason').input('Synthetic fidelity check')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    after = repo.get_quota_transaction(target)
    assert pd.isna(after['PRICE']) if expected is None else after['PRICE'] == expected
    assert Decimal(str(after['QUOTA_COUNT'])) == Decimal('2.125')


@pytest.mark.parametrize('before,entered,expected', [(0, '', None), (None, '0', Decimal(0))])
def test_explicit_edit_can_change_zero_to_null_or_null_to_zero(chain, tmp_path, monkeypatch, before, entered, expected):
    repo, account, other, facility, quota, flock, _ = chain
    target = repo.upsert_quota_transaction(dict(QUOTA_ID=quota, TRANSACTION_TYPE='Purchase',
        QUOTA_COUNT=2, EFFECTIVE_DATE='2026-01-01', RELATED_ACCOUNT_ID=other, PRICE=before))
    app = quota_app(repo, tmp_path, monkeypatch, 'edit', target)
    app.text_input(key='quota_tx_form_price').input(entered)
    app.text_input(key='quota_tx_form_revision_reason').input('Synthetic price correction')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    after = repo.get_quota_transaction(target)
    assert pd.isna(after['PRICE']) if expected is None else after['PRICE'] == expected
    history = repo.get_record_revisions()
    assert len(history) == 1
    after_price = history.iloc[0].AFTER_DATA['PRICE']
    assert pd.isna(after_price) if expected is None else after_price == expected


def test_legacy_credit_decimal_and_optional_account_are_visible_and_preserved(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, _ = chain
    row = dict(QUOTA_TRANSACTION_ID='synthetic-legacy', QUOTA_ID=quota, OWNER_ACCOUNT_ID=account,
               TRANSACTION_TYPE='Base', QUOTA_COUNT=Decimal('1234.1250'), PRICE=None,
               QUOTA_LEASE_TYPE='Non One Time Credit', EFFECTIVE_DATE='2020-01-01',
               RELATED_ACCOUNT_ID=None, COMMENTS='old', UPDATED_AT='2026-01-01T00:00:00.123456789')
    repo._quota_transactions = pd.concat([repo._quota_transactions, pd.DataFrame([row])], ignore_index=True)
    app = quota_app(repo, tmp_path, monkeypatch, 'edit', row['QUOTA_TRANSACTION_ID'])
    assert not app.exception and not app.error
    assert app.selectbox(key='quota_tx_form_lease').value == 'Non One Time Credit'
    assert app.selectbox(key='quota_tx_form_related_account').label == 'Related Account'
    assert app.text_input(key='quota_tx_form_count').value == '1234.1250'
    app.text_area(key='quota_tx_form_comments').input('Synthetic corrected notes')
    app.text_input(key='quota_tx_form_revision_reason').input('Synthetic legacy field preservation')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    saved = repo.get_quota_transaction(row['QUOTA_TRANSACTION_ID'])
    assert saved['QUOTA_LEASE_TYPE'] == row['QUOTA_LEASE_TYPE']
    assert saved['QUOTA_COUNT'] == row['QUOTA_COUNT'] and pd.isna(saved['PRICE'])
    assert any('1,234.125' in m.value for m in app.markdown)
    app.session_state['_efns_record_8_Quota_Transactions_view'] = 'list'
    app.run()
    assert not app.exception
    assert any('1,234.125' in f.value.get('QUOTA_COUNT', pd.Series(dtype=object)).tolist()
               for f in app.dataframe)
