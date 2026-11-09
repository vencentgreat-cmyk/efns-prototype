# Trial readiness: static NULL / empty-data scan

Scope: all Python files directly under `app/pages/` and `app/services/`, reviewed for text-method calls, numeric conversions, first-element indexing and division. These are conditional risks from static inspection, not reproduced staff failures. No changes were made to these sites. Database column types, parser contracts or normal widget return types may exclude some conditions.

| File | Line | Condition and risk |
| --- | ---: | --- |
| `app/services/flock_date_repair_workspace.py` | 19–22 | A short CSV row can leave FLOCK_ID or REASON as None despite valid headers; `.strip()` then raises. The upload handler catches ValueError/UnicodeError, not AttributeError. |
| `app/pages/6_Flock_Transactions.py` | 95 | None/NaN are guarded, but nonnumeric or infinite stored QUANTITY reaches `int()` and can raise, even though quantity_default is unused. Typed CORE quantities normally prevent malformed text. |
| `app/pages/8_Quota_Transactions.py` | 228 | New-record numeric default uses `float(value or 0)`; pandas NA has ambiguous truth, and nonnumeric text raises. Normal new-record defaults are empty; risk depends on malformed/stale current-record data. |
| `app/pages/9_Salmonella_Tests.py` | 109, 144 | Sample count uses `int(value or 0)`; pandas NA truth testing or NaN/nonnumeric conversion can raise. Line 144 is the new-record branch; line 109 displays a selected record. |
| `app/services/revision_history.py` | 79 | `_short_id` evaluates `value or ''`; pandas NA cannot be truth-tested. Normal non-null primary keys prevent this; nullable/malformed candidate frames can raise. |
| `app/services/historical_correction_workspace.py` | 58 | `int(row.get('DECISION_VERSION') or 0)` can raise for pandas NA, NaN or malformed numeric text. Depends on backend/version-column contract. |
| `app/services/production_reports.py` | 238 | `int(year)` raises for None or malformed year on a direct builder call. The report page supplies a bounded number widget; default-parameter smoke tests pass. |
| `app/pages/1_Production_Import.py` | 172–173 | `.dropna().astype(int)` rejects non-null nonnumeric/infinite reporting periods if they reach the normalized frame. The first-element reads that follow are length-guarded. |

The report sorting `.isdecimal()` sites reviewed receive normalized strings. Reviewed report utilization divisions guard unknown/zero denominators; no additional unguarded zero-denominator site was identified. Streamlit column indexing, explicit empty guards and text-input `.strip()` calls were excluded from the findings because their immediate contracts provide the necessary values. `14_Source_Data_Profiler.py:67` uses `sheet_names[0]`, but its reader (`data/profiling.py:110`) rejects an empty worksheet dictionary before that point, so this is not listed as a current risk.

Automated smoke coverage is separate: all 23 Available catalog entries are exercised through pure builders and authenticated report pages using normal, empty, nullable and nonmatching-range data. Reports whose account eligibility intentionally ignores dates may retain account rows in a nonmatching transaction range; this scan does not change that rule. Quota-history balances likewise retain eligible account context. Required account/grader selectors show guidance when no selection is possible.
