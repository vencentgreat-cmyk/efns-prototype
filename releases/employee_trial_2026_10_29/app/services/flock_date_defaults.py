"""Editable Flock form defaults, independent of validation and report rules."""
from datetime import date, datetime, timedelta


# Legacy data observations: Placement = Hatch + 19 weeks, Estimated Disposal =
# Placement + 52 weeks. Staff confirmation is pending; these are defaults only.
PLACEMENT_DEFAULT_DAYS = 133
ESTIMATED_DISPOSAL_DEFAULT_DAYS = 364


def _date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    return value if isinstance(value, date) else date.fromisoformat(value)


def placement_from_hatch(hatch):
    hatch = _date(hatch)
    return hatch + timedelta(days=PLACEMENT_DEFAULT_DAYS) if hatch else None


def estimated_disposal_from_placement(placement):
    placement = _date(placement)
    return placement + timedelta(days=ESTIMATED_DISPOSAL_DEFAULT_DAYS) if placement else None


def apply_flock_date_defaults(hatch, placement=None, estimated=None, *,
                              placement_manual=True, estimated_manual=True,
                              editing=False):
    """Follow upstream dates until overridden; clearing re-enables a default.

    Callers track whether each value was manually edited. Existing nonempty
    inputs are preserved by default. Edit mode returns stored values untouched.
    """
    if editing:
        return placement, estimated
    if not _date(placement) or not placement_manual:
        placement = placement_from_hatch(hatch)
    if not _date(estimated) or not estimated_manual:
        estimated = estimated_disposal_from_placement(placement)
    return placement, estimated
