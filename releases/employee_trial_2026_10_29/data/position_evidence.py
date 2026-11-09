"""Pure review helpers. Unknown source coverage never means zero missing rows."""
import datetime as dt
from decimal import Decimal, InvalidOperation

import pandas as pd

from data.producer_identity import text


def guid(value):
    value = text(value)
    return value.casefold() if value else None


def number(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (ValueError, TypeError, InvalidOperation):
        return None


def day(value):
    """Use the supplied date part, without timezone conversion."""
    value = text(value)
    try:
        return dt.date.fromisoformat(value[:10]) if value else None
    except ValueError:
        return None


def records(frame):
    return frame.to_dict('records') if isinstance(frame, pd.DataFrame) else list(frame or [])


def inactive(row):
    return any(guid(row.get(key)) in {'inactive', '1'}
               for key in ('RAW_STATECODE', 'STATECODE', 'STATECODE_DISPLAYNAME'))


def known_sum(values):
    """All unknown remains unknown; a real zero remains zero."""
    known = [value for value in values if value is not None]
    return sum(known, Decimal(0)) if known else None
