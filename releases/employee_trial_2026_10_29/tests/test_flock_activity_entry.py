"""Urgent C regression cases: local pages, synthetic records only."""
import datetime as dt
import pytest

from data.business_time import halifax_today
from tests.test_staff_workflows import chain
from tests.test_review_integrated import new_transaction_page


@pytest.mark.parametrize('kind', ['Count', 'Removal'])
@pytest.mark.parametrize('offset', [-1, 1])
def test_non_today_entry_clears_stale_confirmation_and_saves_activity(chain, tmp_path, monkeypatch, kind, offset):
    r, _, _, _, _, fid, _ = chain
    app = new_transaction_page(r, tmp_path, monkeypatch)
    app.selectbox(key='flock_tx_form_type').select(kind).run()
    app.number_input(key='flock_tx_form_quantity').set_value(2)
    app.checkbox(key='flock_tx_form_apply_'+fid).check().run()
    app.date_input(key='flock_tx_form_date').set_value(halifax_today()+dt.timedelta(days=offset)).run()
    box = app.checkbox(key='flock_tx_form_apply_'+fid)
    assert box.disabled and not box.value
    assert not app.session_state['flock_tx_form_quantity_intent']
    assert any("Only today's Count/Removal" in x.value for x in app.caption)
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_flock_transactions(fid)) == 1 and r.get_flock(fid)['BIRD_COUNT'] == 10
    assert any('Bird Count was not changed' in x.value for x in app.info)


def test_current_quantity_applies_once_and_new_form_resets_date(chain, tmp_path, monkeypatch):
    r, _, _, _, _, fid, _ = chain
    app = new_transaction_page(r, tmp_path, monkeypatch)
    app.number_input(key='flock_tx_form_quantity').set_value(7)
    app.checkbox(key='flock_tx_form_apply_'+fid).check()
    app.text_input(key='flock_tx_form_quantity_reason').input('Synthetic confirmed observation')
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    app.run()
    assert r.get_flock(fid)['BIRD_COUNT'] == 7 and len(r.get_flock_transactions(fid)) == 1
    app.button(key='flock_tx_record_back').click().run()
    app.button(key='flock_tx_list_new').click().run()
    app.date_input(key='flock_tx_form_date').set_value(halifax_today()-dt.timedelta(days=3)).run()
    app.button(key='flock_tx_record_cancel').click().run()
    app.button(key='flock_tx_list_new').click().run()
    assert app.date_input(key='flock_tx_form_date').value == halifax_today()
    assert not app.checkbox(key='flock_tx_form_apply_'+fid).value


def test_failed_current_save_does_not_leave_activity_retry_stuck(chain, tmp_path, monkeypatch):
    r, _, _, _, _, fid, _ = chain
    app = new_transaction_page(r, tmp_path, monkeypatch)
    app.number_input(key='flock_tx_form_quantity').set_value(7)
    app.checkbox(key='flock_tx_form_apply_'+fid).check()
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and app.error and r.get_flock_transactions(fid).empty
    assert not app.session_state['flock_tx_form_quantity_intent']
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_flock_transactions(fid)) == 1 and r.get_flock(fid)['BIRD_COUNT'] == 10
    assert any('Bird Count was not changed' in x.value for x in app.info)


@pytest.mark.parametrize('kind', ['Delivery', 'Sale'])
def test_delivery_sale_remain_activity_only(chain, tmp_path, monkeypatch, kind):
    r, _, _, _, _, fid, _ = chain
    app = new_transaction_page(r, tmp_path, monkeypatch)
    app.selectbox(key='flock_tx_form_type').select(kind).run()
    assert not app.checkbox
    app.number_input(key='flock_tx_form_quantity').set_value(2)
    app.button(key='flock_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert len(r.get_flock_transactions(fid)) == 1 and r.get_flock(fid)['BIRD_COUNT'] == 10
    assert any('Bird Count was not changed' in x.value for x in app.info)
