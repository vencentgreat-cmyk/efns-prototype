# Trial build — 2026-11-04

Branch: `codex-trial-build-20261104`. Integration merge:
`5627e3a9bb9ffbebd1d271528acfc5af334f2562`.
Work only in `releases/employee_trial_2026_10_29`.

## Included source branches

| Branch | Included commit | Integration |
|---|---|---|
| `codex-production-blank-rows-20261104` | `365ffb35ba9fdc2e8953193564de28888de847b3` | Trial branch base. |
| `codex-producer-active-match-20261104` | `9c1900e2a314f0251646251ed5927c5b66071cca` | Merged into the trial branch. |
| `codex-flock-current-report-20261104` | `0d0a0441921f1df1ea34f56e82516363fb2f8887` | Already included through the base; merge reported up to date. |
| `codex-history-polish-r2-20261104` | `d9eda0b7345de64a9583448fd5bdfda0692d1612` | Already included through the base; merge reported up to date. |

Only the expected `DELIVERY_RUNTIME_DIFF_20261030.json` conflict required
resolution: both incoming entries were retained. All 35 candidate runtime
hashes, including follow-up entries, were recomputed against merged files and
matched their stored values. No manual application-code edits were made.

## Staff-visible changes

- Report Center now provides Flock Current Report with date, mortality and quota
  type parameters, exact inventory arithmetic, subtotals and CSV/XLSX exports.
  Its inclusion policy remains explicitly provisional.
- Production Import ignores entirely blank/whitespace-only workbook rows while
  preserving original Excel row numbers and errors on partially populated rows.
- Duplicate exact producer registration matches select the sole Active Account
  (case-insensitive); ambiguous matches remain unresolved. Matching evidence
  records ignored Account IDs. GUID matching remains unchanged.
- Record History uses staff names/email where available, falls back to stored
  IDs when lookup is missing/fails, and offers recognizable record labels.

## Offline verification

From the release directory, `../../.venv/Scripts/python.exe -m pytest -q`:
**1234 passed, 1 skipped, 0 failed; 31 warnings; 237.14 seconds**.
The full run includes all **25 tests in `tests/test_eims_migration.py`**.
These are synthetic/offline checks, not company-data or browser acceptance.
No Snowflake connection, deployment, SQL execution or data change was performed.

## Required manual re-tests — pending

| Step | Action | Expected result | Status |
|---|---|---|---|
| 1 | Upload `EIMS Production Upload (4).xlsm` for Production Import review. | 0 errors, 0 warnings, 58 rows, all `UNIQUE_MATCHED`. | Pending; actual result TBC. |
| 2 | Run Flock Current Report for Bayview Poultry Farm Ltd and compare with legacy using the same report date, mortality and quota type. | Compare detail values and subtotals; record discrepancies. Actual company-data parity TBC. | Pending. |
| 3 | Open Record History and inspect Changed by. | Names/email for resolvable users; ID fallback for missing/failed lookup. | Pending. |

The manual re-tests above have not been executed by this task. Upload review
does not authorize committing business rows. Deployment remains user-operated.
