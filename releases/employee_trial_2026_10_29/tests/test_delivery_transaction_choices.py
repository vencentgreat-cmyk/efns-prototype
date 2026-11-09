"""Current entry choices and historical editing remain separate contracts."""
import pandas as pd
import pytest

from data.constants import QUOTA_TRANSACTION_TYPES, UNASSIGNED_LABEL
from data.validation import validate_quota_transaction
from tests.test_daily_quota_entry import quota_app
from tests.test_staff_workflows import chain


def test_exact_current_choices():
    assert QUOTA_TRANSACTION_TYPES == ('Adjustment','Purchase','Sale','Lease (In)','Lease (Out)','Base')


@pytest.mark.parametrize('kind', [*QUOTA_TRANSACTION_TYPES, 'Lease In', 'Lease Out'])
def test_daily_accepts_supported_types_and_legacy_lease_names(chain, kind):
    repo, account, other, facility, quota, *_ = chain
    record = dict(QUOTA_ID=quota,TRANSACTION_TYPE=kind,QUOTA_COUNT=5,
                  RELATED_ACCOUNT_ID=other,EFFECTIVE_DATE='2026-01-01',END_DATE='2026-12-31')
    assert not validate_quota_transaction(repo,record)


@pytest.mark.parametrize('kind', ['Global Adjustment','Terminate Quota','National Allocation','Provincial Allocation'])
def test_historical_or_allocation_type_not_new_entry_choice(chain,kind):
    repo, account, other, facility, quota, *_ = chain
    errors=validate_quota_transaction(repo,dict(QUOTA_ID=quota,TRANSACTION_TYPE=kind,
        QUOTA_COUNT=5,RELATED_ACCOUNT_ID=other,EFFECTIVE_DATE='2026-01-01'))
    assert 'Transaction Type is required.' in errors


@pytest.mark.parametrize('kind', ['Lease In','Lease Out','Global Adjustment','Terminate Quota'])
def test_historical_type_unchanged_edit_retained(chain,tmp_path,monkeypatch,kind):
    repo, account, other, facility, quota, *_ = chain
    row=dict(QUOTA_TRANSACTION_ID='DEV_TEST old transaction',QUOTA_ID=quota,OWNER_ACCOUNT_ID=account,
             TRANSACTION_TYPE=kind,QUOTA_COUNT=0 if kind=='Terminate Quota' else 5,
             RELATED_ACCOUNT_ID=other,QUOTA_LEASE_TYPE='Non One Time Credit',PRICE=None,
             EFFECTIVE_DATE='2020-01-01',END_DATE=None,UPDATED_AT='2026-01-01T00:00:00.123456789')
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame([row])],ignore_index=True)
    app=quota_app(repo,tmp_path,monkeypatch,'edit',row['QUOTA_TRANSACTION_ID'])
    assert not app.exception and app.selectbox(key='quota_tx_form_type').value==kind
    app.text_area(key='quota_tx_form_comments').input('DEV_TEST historical notes')
    app.text_input(key='quota_tx_form_revision_reason').input('DEV_TEST preserve historical type')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    saved=repo.get_quota_transaction(row['QUOTA_TRANSACTION_ID'])
    assert saved['TRANSACTION_TYPE']==kind and saved['QUOTA_COUNT']==row['QUOTA_COUNT']


def test_new_type_change_updates_optional_counterparty_label(chain,tmp_path,monkeypatch):
    repo,*_=chain
    app=quota_app(repo,tmp_path,monkeypatch)
    assert app.selectbox(key='quota_tx_form_type').options==list(QUOTA_TRANSACTION_TYPES)
    assert app.selectbox(key='quota_tx_form_related_account').label=='Related Account'
    app.selectbox(key='quota_tx_form_type').select('Lease (In)').run()
    assert app.selectbox(key='quota_tx_form_related_account').label=='Related Account *'
    app.selectbox(key='quota_tx_form_type').select('Base').run()
    assert app.selectbox(key='quota_tx_form_related_account').label=='Related Account'
