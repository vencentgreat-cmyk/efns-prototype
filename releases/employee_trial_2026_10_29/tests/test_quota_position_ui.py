"""Employee pages with synthetic Mock records; never company browser evidence."""
from pathlib import Path

import pandas as pd

from tests.auth_support import authenticated_app
from tests.test_staff_workflows import chain


def test_historical_type_filter_and_credit_label_without_blind_sum(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, _ = chain
    # Simulate historically imported types, not an expansion of daily choices.
    rows = []
    for i, (kind, qty) in enumerate([('Base', 100), ('Adjustment', -3), ('Lease (Out)', 7)]):
        rows.append(dict(QUOTA_TRANSACTION_ID=f'synthetic-{i}', QUOTA_ID=quota,
                         OWNER_ACCOUNT_ID=account, RELATED_ACCOUNT_ID=other,
                         TRANSACTION_TYPE=kind, QUOTA_COUNT=qty, EFFECTIVE_DATE='2026-01-01',
                         END_DATE='2026-12-31', PRICE=0, QUOTA_LEASE_TYPE='Fixed Term'))
    repo._quota_transactions = pd.concat([repo._quota_transactions, pd.DataFrame(rows)], ignore_index=True)
    app = authenticated_app(Path(__file__).resolve().parents[1] / 'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repo
    app.switch_page('app/pages/8_Quota_Transactions.py').run()
    assert not app.exception and not app.error
    options = app.selectbox(key='quota_tx_filter_transaction_type').options
    assert all(kind in options for kind in ('Base', 'Adjustment', 'Lease (Out)'))
    assert not any(metric.label == 'Filtered quantity' for metric in app.metric)
    app.selectbox(key='quota_tx_filter_transaction_type').select('Adjustment').run()
    assert not app.exception and not app.error
    assert app.metric[0].value == '1'
    assert any(-3 in frame.value.get('Recorded quantity', pd.Series(dtype=object)).tolist()
               for frame in app.dataframe)
    app.session_state['_efns_record_8_Quota_Transactions_view'] = 'detail'
    app.session_state['_efns_record_8_Quota_Transactions_id'] = 'synthetic-2'
    app.run()
    assert not app.exception and any('**Credit Type**' in md.value for md in app.markdown)


def test_flock_latest_multisource_observation_is_not_auto_selected(chain, tmp_path, monkeypatch):
    repo, account, other, facility, quota, flock, _ = chain
    from data.business_time import halifax_today
    for i, source in enumerate(('Producer', 'Board')):
        repo._flock_transactions = pd.concat([repo._flock_transactions, pd.DataFrame([dict(
            FLOCK_TRANSACTION_ID=f'synthetic-count-{i}', FLOCK_ID=flock,
            TRANSACTION_TYPE='Count', TRANSACTION_DATE=halifax_today(), QUANTITY=10,
            COUNT_SOURCE_LABEL=source)])], ignore_index=True)
    before = repo._flocks.copy(deep=True)
    app = authenticated_app(Path(__file__).resolve().parents[1] / 'streamlit_app.py', tmp_path, monkeypatch)
    app.session_state['_base_repo'] = repo
    app.session_state['_efns_record_5_Flocks_view'] = 'detail'
    app.session_state['_efns_record_5_Flocks_id'] = flock
    app.switch_page('app/pages/5_Flocks.py').run()
    assert not app.exception and not app.error
    assert any('same-day source/quantity conflict' in w.value for w in app.warning)
    assert any(m.label == 'Usage percentage' and m.value == 'Not established' for m in app.metric)
    pd.testing.assert_frame_equal(repo._flocks, before)
