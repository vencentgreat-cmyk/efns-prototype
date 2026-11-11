"""Synthetic date defaults and real Flock form rerun/save regressions."""
from datetime import date, timedelta

import pytest

from app.services.flock_date_defaults import (
    PLACEMENT_DEFAULT_DAYS, ESTIMATED_DISPOSAL_DEFAULT_DAYS,
    placement_from_hatch, estimated_disposal_from_placement,
    apply_flock_date_defaults,
)
from tests.test_sara_feedback import entry_app
from tests.test_staff_workflows import chain


@pytest.mark.parametrize("hatch,placement,estimated", [
    (date(2023,10,19), date(2024,2,29), date(2025,2,27)),
    (date(2024,2,29), date(2024,7,11), date(2025,7,10)),
    (date(2026,1,31), date(2026,6,13), date(2027,6,12)),
])
def test_calendar_defaults(hatch, placement, estimated):
    assert placement_from_hatch(hatch) == placement
    assert estimated_disposal_from_placement(placement) == estimated
    assert apply_flock_date_defaults(hatch) == (placement, estimated)
    assert placement - hatch == timedelta(days=PLACEMENT_DEFAULT_DAYS)
    assert estimated - placement == timedelta(days=ESTIMATED_DISPOSAL_DEFAULT_DAYS)


@pytest.mark.parametrize("empty", [None, ""])
def test_empty_dates(empty):
    assert placement_from_hatch(empty) is None
    assert estimated_disposal_from_placement(empty) is None
    assert apply_flock_date_defaults(empty, empty, empty) == (None, None)


def test_manual_overrides_and_clearing():
    hatch = date(2026,1,1)
    placement, estimated = date(2026,6,1), date(2028,3,1)
    assert apply_flock_date_defaults(hatch, placement, estimated) == (placement, estimated)
    # Generated values follow changes until manually overridden.
    assert apply_flock_date_defaults(hatch, placement, estimated,
        placement_manual=False, estimated_manual=False) == (date(2026,5,14),date(2027,5,13))
    assert apply_flock_date_defaults(hatch, placement, None) == (placement,date(2027,5,31))
    assert apply_flock_date_defaults(hatch, None, estimated) == (date(2026,5,14),estimated)


@pytest.mark.parametrize("placement,estimated", [(None,None),(date(2025,3,1),date(2028,3,1))])
def test_edit_does_not_overwrite_even_empty_dates(placement, estimated):
    assert apply_flock_date_defaults(date(2026,1,1),placement,estimated,
        placement_manual=False,estimated_manual=False,editing=True) == (placement,estimated)


def test_create_reruns_overrides_and_clear(chain,tmp_path,monkeypatch):
    repo,*_ = chain
    app = entry_app(repo,tmp_path,monkeypatch,'5_Flocks')
    assert not app.exception
    app.date_input(key='flock_form_hatch').set_value(date(2026,1,1)).run()
    assert app.date_input(key='flock_form_placement').value == date(2026,5,14)
    assert app.date_input(key='flock_form_est_disposal').value == date(2027,5,13)
    app.date_input(key='flock_form_placement').set_value(date(2026,6,1)).run()
    assert app.date_input(key='flock_form_est_disposal').value == date(2027,5,31)
    app.date_input(key='flock_form_hatch').set_value(date(2026,2,1)).run()
    assert app.date_input(key='flock_form_placement').value == date(2026,6,1)
    app.date_input(key='flock_form_est_disposal').set_value(date(2028,1,1)).run()
    app.date_input(key='flock_form_placement').set_value(date(2026,7,1)).run()
    assert app.date_input(key='flock_form_est_disposal').value == date(2028,1,1)
    app.date_input(key='flock_form_placement').set_value(None).run()
    assert app.date_input(key='flock_form_placement').value == date(2026,6,14)
    assert app.date_input(key='flock_form_est_disposal').value == date(2028,1,1)
    app.date_input(key='flock_form_est_disposal').set_value(None).run()
    assert app.date_input(key='flock_form_est_disposal').value == date(2027,6,13)
    assert not app.exception


@pytest.mark.parametrize("stored_placement,stored_estimated", [
    (None,None), (date(2026,6,1),date(2028,1,1)),
    (date(2026,5,14),date(2027,5,13)),
])
def test_edit_preserves_stored_dates_and_comparison_captions(chain,tmp_path,monkeypatch,
                                                          stored_placement,stored_estimated):
    repo,_,_,_,_,flock,_ = chain
    row = repo._flocks.FLOCK_ID.eq(flock)
    repo._flocks.loc[row,'PLACEMENT_DATE'] = stored_placement
    repo._flocks.loc[row,'EST_DISPOSAL'] = stored_estimated
    app = entry_app(repo,tmp_path,monkeypatch,'5_Flocks','edit',flock)
    assert not app.exception
    assert app.date_input(key='flock_form_placement').value == stored_placement
    assert app.date_input(key='flock_form_est_disposal').value == stored_estimated
    captions = [c.value for c in app.caption]
    assert ('Calculated from Hatch Date: 2026-05-14' in captions) == (stored_placement != date(2026,5,14))
    expected = estimated_disposal_from_placement(stored_placement)
    assert any(c.startswith('Calculated from Placement Date:') for c in captions) == bool(expected and expected != stored_estimated)
    # Changing another field and saving must not materialize defaults in edits.
    app.text_area(key='flock_form_comments').input('Synthetic date preservation')
    app.text_input(key='flock_form_revision_reason').input('Synthetic comment change')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    saved = repo.get_flock(flock)
    assert saved['PLACEMENT_DATE'] == stored_placement
    assert saved['EST_DISPOSAL'] == stored_estimated


def test_create_save_uses_defaults_without_initial_position_or_delivery(chain,tmp_path,monkeypatch):
    repo,*_ = chain
    before_transactions = repo.get_flock_transactions().copy()
    app = entry_app(repo,tmp_path,monkeypatch,'5_Flocks')
    app.text_input(key='flock_form_number').input('SYNTHETIC date defaults')
    app.text_input(key='flock_form_permit').input('SYNTHETIC date permit')
    app.number_input(key='flock_form_birds').set_value(10)
    app.date_input(key='flock_form_hatch').set_value(date(2026,1,1)).run()
    assert not app.checkbox(key='flock_form_initial_confirmed').value
    assert not app.checkbox(key='flock_form_delivery').value
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    saved = repo.get_flocks().loc[lambda frame: frame.FLOCK_NUMBER.eq('SYNTHETIC date defaults')].iloc[0]
    assert saved.PLACEMENT_DATE == date(2026,5,14)
    assert saved.EST_DISPOSAL == date(2027,5,13)
    assert repo.get_flock_transactions().equals(before_transactions)


def test_create_defaults_keep_explicit_initial_position_and_delivery_selection(chain,tmp_path,monkeypatch):
    repo,*_ = chain
    app = entry_app(repo,tmp_path,monkeypatch,'5_Flocks')
    app.text_input(key='flock_form_number').input('SYNTHETIC confirmed dates')
    app.text_input(key='flock_form_permit').input('SYNTHETIC confirmed permit')
    app.number_input(key='flock_form_birds').set_value(10)
    app.date_input(key='flock_form_hatch').set_value(date(2026,1,1)).run()
    app.checkbox(key='flock_form_delivery').check()
    app.checkbox(key='flock_form_initial_confirmed').check()
    app.text_input(key='flock_form_initial_reason').input('Synthetic confirmed placement evidence')
    app.button(key='flock_record_save').click().run()
    assert not app.exception and not app.error
    saved = repo.get_flocks().loc[lambda frame: frame.FLOCK_NUMBER.eq('SYNTHETIC confirmed dates')].iloc[0]
    assert saved.PLACEMENT_DATE == date(2026,5,14)
    assert saved.CREATE_DELIVERY_TRANSACTION
    events = repo.get_flock_events(saved.FLOCK_ID)
    assert len(events) == 1 and events.iloc[0].EVENT_TYPE == 'INITIAL_POSITION'
    # Existing confirmed initial time stays noon Halifax (15:00 UTC in May).
    assert events.iloc[0].EFFECTIVE_AT.isoformat().startswith('2026-05-14T15:00:00')
