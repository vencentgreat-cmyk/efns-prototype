"""Explicit business-date and precise version contracts, independent of host TZ."""
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd

def halifax_today(now=None):
    instant=now if now is not None else dt.datetime.now(dt.timezone.utc)
    stamp=pd.Timestamp(instant)
    if stamp.tzinfo is None:
        raise ValueError('A timezone-aware instant is required.')
    return stamp.tz_convert(ZoneInfo('America/Halifax')).date()

def version_bind(value):
    if value is None or pd.isna(value):return None
    stamp=pd.Timestamp(value)
    if stamp.tzinfo is not None:stamp=stamp.tz_convert('UTC').tz_localize(None)
    return stamp.isoformat()

def same_value(left,right):
    if left is None or pd.isna(left):return right is None or bool(pd.isna(right))
    if right is None or pd.isna(right):return False
    return bool(left==right)
