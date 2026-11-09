"""Actual local component labels; synthetic identities only."""
import pandas as pd
from tests.test_staff_workflows import chain
from tests.test_daily_quota_entry import quota_app


def test_component_owner_name_and_unknown_identity_fallback(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,*_=chain
    repo.upsert_quota_transaction(dict(QUOTA_ID=quota,TRANSACTION_TYPE='Adjustment',
        QUOTA_COUNT=-5,PRICE=None,EFFECTIVE_DATE='2026-01-01'))
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame([dict(
        QUOTA_TRANSACTION_ID='DEV_TEST unknown owner',OWNER_ACCOUNT_ID='DEV_TEST unmapped',
        TRANSACTION_TYPE='Base',QUOTA_COUNT=3)])],ignore_index=True)
    app=quota_app(repo,tmp_path,monkeypatch,'list')
    assert not app.exception and not app.error
    frame=next(f.value for f in app.dataframe if 'Recorded quantity' in f.value)
    assert 'Owner Account ID' not in frame and 'Owner Account' in frame
    assert repo.get_account(account)['ORGANIZATION_NAME'] in frame['Owner Account'].tolist()
    assert 'DEV_TEST unmapped' in frame['Owner Account'].tolist()
    assert any(c.value=='Totals by type for the filtered owner records. This is not an available quota balance.' for c in app.caption)
