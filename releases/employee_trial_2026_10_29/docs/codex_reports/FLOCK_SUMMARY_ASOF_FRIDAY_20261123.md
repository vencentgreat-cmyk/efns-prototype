# Flock Summary Friday snapshot — 2026-11-23

Branch: `codex-flock-summary-asof-friday-20261123`; base origin/main `77311823a8dfb1cdf5059bf8feb36a491485bf82`.

## Staff decision and implementation

Flock Summary now takes each week's inventory snapshot on Friday, five days after the maintained EFC Sunday start. For week 202601, the week still spans 2025-12-28 through 2026-01-03 and the inventory/As-of Date is 2026-01-02.

The old INVENTORY_AS_OF_WEEK_DAY constant was also used to validate the calendar's Saturday end; changing it alone would reject valid seven-day calendars. It is now Python weekday 4 (Friday), while a separate EFC_WEEK_END_WEEK_DAY remains Python weekday 5 (Saturday). The builder derives Friday from the validated start and uses that same date for both the existing Flock Status builder and the As-of Date column. Calendar generation, week boundaries, validation scope, current-week/default selection, continuity and 52/53-week handling are unchanged.

## Complete reference / caller audit

| Place | Treatment |
| --- | --- |
| `data/efc_calendar.py`: INVENTORY_AS_OF_WEEK_DAY | Friday, Python weekday 4 = Sunday start + 5 days. |
| `data/efc_calendar.py`: WEEKLY_INVENTORY_CAPTION | Friday wording, explicitly start + 5 days. |
| `data/efc_calendar.py`: _validated_week | Calendar end uses the separate Saturday constant, retaining seven-day Sunday-Saturday validation and messages. |
| `app/services/flock_summary_report.py`: week loop / Status call | Selects Friday instead of the returned Saturday boundary. |
| Same builder: As-of Date and result.attrs['notes'] | Friday date and shared Friday caption; no change to columns, grouping, quotas/types or weekly aggregation. |
| `app/services/report_center.py`: flock-summary catalog description | Weekly Friday inventory snapshots; never summed across weeks. |
| `app/pages/4_Reports.py`: imported caption, on-screen caption, saved run parameters and note filtering | Automatically use the shared Friday wording; page source unchanged. |
| Same page: downloads / CSV | Same result frame and column structure; As-of Date now Friday. No extra CSV heading or note rows. |
| Same page: XLSX Notes and PDF subtitle/notes | Shared Friday caption and frame. Export modules/page source unchanged. |
| `tests/test_flock_summary_report.py`: Status comparison dates | Compare against Friday, retaining existing inventory/type/grouping invariants. |
| `tests/test_flock_summary_friday.py` | Synthetic Count cutoff, date/example, all formats, producer grouping, never summing weeks, 52/53-week boundaries and both UI entrypoints. |
| `tests/test_efc_calendar_scope.py`, `tests/test_report_smoke.py` | Existing callers use the updated builder; Sunday-Saturday calendar assertions remain correct and unchanged. |
| `docs/codex_reports/FLOCK_SUMMARY_LEASE_ADJUST_20261120.md` | Inventory-date, week-end snapshot and export-caption statements updated to Friday, identifying the new staff decision. |
| `docs/codex_reports/FLOCK_SUMMARY_CALENDAR_FIX_20261120.md` | Describes unchanged calendar validation, not a Saturday snapshot rule; retained as historical evidence. |

Search of app/data/tests/docs found no other runtime Saturday snapshot wording or as-of-day consumers. Remaining Saturday references describe the unchanged calendar, or explicitly test exclusion of a Saturday observation from Friday's snapshot.

## Unchanged behavior

The only numeric change is the intended consequence of evaluating Flock Summary one day earlier (including its existing observation cutoff, mortality, placement and disposal handling). No other report's numbers or calculation are changed. Group by producer, quota-type columns, within-week grouping and the prohibition on summing stock across weeks remain intact. Lease/adjustment and confirmed quota rules, repository reads, SQL, stored records, permissions and export formatting are unchanged. No real data, DDL, Snowflake access, deployment or PR.

## Validation

Synthetic data only; no real-data or legacy fixtures added. Focused suite: 39 passed. Full release suite (Python 3.12): 2,486 passed, 1 skipped, 0 failed, 0 errors. Full root suite (Python 3.11): 706 passed, 0 skipped, 0 failed, 0 errors. Manifest: 170 candidate hashes. Only the authorized Flock Summary date expectations changed; other report fixture expectations are untouched. Manifest regenerated from base main with every candidate hash recalculated from LF-normalized current file bytes; existing entries retained.

## Shipped-file comparison

132 shipped files checked against the base Git tree (LF-normalized text; binary assets unchanged). 129 are unchanged; only these three runtime files differ.

| Path | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `app/services/flock_summary_report.py` | `56fe6b228ab82bc6538c45cdf49ba32c2e2415f391f41b1ecee8312f21ac74db` | `d3d288e747d7af9c9dbef4c597b954eeff1bac29a27c47513f9989b00bcf617f` |
| `app/services/report_center.py` | `05254edf5be1d917b7a16089e2ef8bb99cd3aa0706996fad3cc482a04af37694` | `b7a3af568a4061637be6bc6a076e3579e752cf7c81718592f0c768b25ac7a4af` |
| `data/efc_calendar.py` | `8a8361c318e7be09ab48e1581c3638aebca4bb3c9b3c169f49d4c006c94fb06a` | `c4ef27c804ddc514563d4399e8d687cd4c5242fdc6da397eba7f21e9d7ba2760` |
