"""Strict JSON evidence encoding: blanks stay null; source text is not altered."""
import datetime as dt
import json
import math

import pandas as pd


def json_value(value):
    if isinstance(value, dict): return {str(key): json_value(item) for key,item in value.items()}
    if isinstance(value, (list,tuple)): return [json_value(item) for item in value]
    if value is None or value is pd.NA or value is pd.NaT: return None
    if isinstance(value, float) and math.isnan(value): return None
    if isinstance(value, float) and not math.isfinite(value): return str(value)
    if isinstance(value,(dt.date,dt.datetime)): return value.isoformat()
    if hasattr(value,'item'): return json_value(value.item())
    return value


def evidence_json(value):
    return json.dumps(json_value(value),default=str,allow_nan=False,sort_keys=True)
