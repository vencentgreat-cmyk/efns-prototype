"""Explicit business-date and precise version contracts, independent of host TZ."""
import datetime as dt
from zoneinfo import ZoneInfo
import pandas as pd
import re

def advance_version_sql(now_sql):
    """Advance at least one nanosecond even if the server clock repeats."""
    return f'GREATEST({now_sql},DATEADD(nanosecond,1,COALESCE(UPDATED_AT,{now_sql})))'

def precise_version_sql(sql):
    """Keep database version tokens lossless before either driver decodes them."""
    tables='ACCOUNT|CONTACT|FARM_LOCATION|FACILITY|FACILITY_DETAIL|FLOCK|FLOCK_TRANSACTION|QUOTA_REGISTRATION|QUOTA_TRANSACTION|SALMONELLA_TEST|QUOTA_ALLOCATION|DIM_EFC_DATE|PRODUCTION_RECORD'
    target=rf'[A-Z0-9_]+\.[A-Z0-9_]+\.(?:{tables})\b'
    fmt='YYYY-MM-DD"T"HH24:MI:SS.FF9'
    for match in list(re.finditer(rf'\bFROM\s+({target})(?:\s+([A-Z_][A-Z0-9_]*))?',sql,re.I)):
        alias=match[2]
        if alias and alias.upper() not in {'WHERE','JOIN','LEFT','RIGHT','INNER','ORDER','GROUP','LIMIT','UNION'}:
            pattern=rf'(\bSELECT\s+(?:DISTINCT\s+)?){re.escape(alias)}\.\*(?!\s+REPLACE)'
            sql=re.sub(pattern,lambda m:m[1]+f'{alias}.* REPLACE (TO_CHAR({alias}.UPDATED_AT,\'{fmt}\') AS UPDATED_AT)',sql,flags=re.I)
        pattern=rf'(\bSELECT\s+(?:DISTINCT\s+)?)\*(\s+FROM\s+{re.escape(match[1])})'
        sql=re.sub(pattern,lambda m:m[1]+f'* REPLACE (TO_CHAR(UPDATED_AT,\'{fmt}\') AS UPDATED_AT)'+m[2],sql,flags=re.I)
    return sql

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
