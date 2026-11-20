# Flock Summary scoped calendar validation - 20 November 2026

Base: fetched origin/main 0221a73, PR #44; Task 5 commit 0c9bb54 is an ancestor. Branch: codex-flock-summary-calendar-fix-20261120 in its own worktree.

## Cause and fix

The original resolver validated every week in DIM_EFC_DATE before any lookup, default or requested range. Consequently an unrelated malformed final edge invalidated all earlier complete weeks. The real export was not read or copied for this task; tests construct an explicitly synthetic 11-day final-year week.

Single-week lookup now checks only its requested code. Range validation requires explicit Start/End Week, checks every included week, rejects missing codes and date gaps/overlaps, and never inspects unrelated week contents. Errors name the affected week. All validation completes before the inventory builder is called, so an invalid range produces no partial numbers.

Defaults identify and validate only the current week from calendar row dates, even if today's own row is missing. An incomplete current week is reported by name; ambiguous current-week labels are rejected. Week 1 is proposed as the Start Week input but its contents are checked only when the selected report range actually includes it. Thus a bad historical week 1 cannot prevent staff selecting a later valid range. The End Week remains the validated current EFC week, already within its source year's available codes. No ISO-week/date formula is substituted for production calendar data.

## Callers checked

| Caller | Result |
|---|---|
| data/efc_calendar.py:73 resolve_production_week | Validates one requested week only. |
| data/efc_calendar.py:78 default_flock_summary_weeks | Validates the current week only; does not enumerate/validate the year or calendar. |
| app/services/flock_summary_report.py:15 build_flock_summary_report | Supplies the selected inclusive range to efc_weeks; no unscoped scan remains. |
| app/pages/4_Reports.py:333 defaults and its Run Report call | Uses the above helpers; existing ValueError-to-info handling displays the named-week error and clears stale results. Page code unchanged. |
| tests/test_report_smoke.py:100 and tests/test_flock_summary_report.py | Existing resolver/default/report callers remain covered. |
| data/repositories/mock.py:80 | Uses synthetic_efc_calendar only, not validation; unchanged. |

Repository-wide Python search found no other runtime report or script caller of these resolver/validation functions. The service module's calendar-helper re-exports remain available. The internal efc_weeks helper now requires an explicit range so callers cannot accidentally validate the whole table.

## Validation and unchanged behavior

Focused tests: **31 passed**, comprising 21 new synthetic regression cases and the 10 unchanged Flock Summary tests. Coverage includes an 11-day final week outside the request; the same week explicitly requested; missing/invalid days and missing weeks; range gaps/overlaps and a missing year; current-week/default handling; bad historical week 1 outside a selected range; 52/53-week boundaries; and both Streamlit entrypoints. Tests compare complete result frames, notes and CSV bytes against the same clean calendar, and assert the inventory builder is never called for an invalid range.

The inventory/calculation body of build_flock_summary_report (from kinds onward) is byte-identical after newline normalization. No other report builder, inventory/quota rule, rounding, query, repository, mock generator, export helper, permission, authentication, connection or schema is changed. No real data or legacy file was added. No Snowflake access, DDL, deployment or PR.

Full release suite (Python 3.12): **2,410 passed, 1 skipped, 0 failed, 0 errors** (11m38s). Full root suite (Python 3.11): **706 passed, 0 failed, 0 errors** (2m20s). The release increase over main is the 21 new synthetic regression cases; no existing test expectation was weakened or edited. The live manifest contains **161 LF-normalized candidate hashes**; final document edits are followed by regeneration and integrity guards.

Changed files, all within the release directory:

- data/efc_calendar.py
- app/services/flock_summary_report.py
- tests/test_efc_calendar_scope.py
- docs/codex_reports/FLOCK_SUMMARY_CALENDAR_FIX_20261120.md
- DELIVERY_RUNTIME_DIFF_20261030.json

No existing report number, formula, rounding, data selection or export calculation changed. The only behavior change is the scope and messages of calendar validation. Valid earlier weeks now work despite an unrelated malformed edge; requested invalid ranges still produce no numbers.

## Shipped-file proof

Only two shipped files differ; all 129 other shipped files are byte-identical. SHA-256 below uses raw worktree bytes; the runtime-diff manifest uses LF-normalized bytes.

| Shipped file | Base SHA-256 | Final SHA-256 |
|---|---|---|
| `app/services/flock_summary_report.py` | `c2169a24b41b25e43ef779bb83c066d9b4dadd8dc590577e3109ed0c0d6673de` | `ad0fad50004ccc8f91ca3faf90664ce2042ba04afc36d79cbaedac9377ef9132` |
| `data/efc_calendar.py` | `dd517e46724e5e7c3de68398113378bfe4f814d93427850c10a6e72efc9a98f2` | `04bd0372364e3875cef5a49beaaa2dea711e4540ee34f2eec749d5c919403dd4` |
