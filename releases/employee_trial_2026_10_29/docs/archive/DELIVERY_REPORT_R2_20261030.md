# Delivery candidate R2 — 30 October 2026

## Scope and status

Branch: `delivery-candidate-r2-20261030`; parent delivery commit:
`89855217d75c80de35d3f4444f4fc3cad59e8c4e`.
Work is confined to `releases/employee_trial_2026_10_29`. No company connection,
SQL execution, data change or deployment was performed. Mock/AppTest and fake
executor results below are offline evidence, not Snowflake transaction/lock or
employee-browser acceptance. All calculation rules remain PENDING.

## Task commits and files

| Task | Commit | Files / outcome |
|---|---|---|
| T1 | `a8c0102` | `tests/test_current_count_zero.py`, `tests/test_spent_fowl_relationship.py`, `tests/test_staff_workflows.py`: align five stale expectations with unestablished current occupancy/usage. Retain zero, retry, revision/audit, export and no-write checks. |
| T2 | `76bb071` | `data/quota_position.py`, `tests/test_r2_rules_loading.py`: missing/invalid rules log a warning and return independent built-in PENDING defaults. |
| T3 | `7031cd5` | `app/services/quota_usage.py`, `app/pages/5_Flocks.py`, `app/pages/8_Quota_Transactions.py`, `tests/test_r2_calculation_guards.py`: failed draft calculations do not block record pages. |
| T4 | `a1487ce` | `data/validation.py`, `data/operational_flock_quota_import.py`, `data/repositories/mock.py`, `data/repositories/snowflake.py`, `tests/test_r2_daily_quota_parity.py`: reuse one changed-field daily quota review at preview and both commit paths. |
| T5 | `82a8f29` | `app/pages/5_Flocks.py`, `app/pages/8_Quota_Transactions.py`, `app/services/quota_usage.py`, `tests/test_r2_usability.py`: owner names with ID fallback; concise captions; full limitations retained in existing expander. |
| T6 | `3c621a0` | `sql/review/quota_flock_reconciliation_20261029.sql`: three header comment lines only; SQL body unchanged. |
| T7 | `e073dbd` | `tests/test_delivery_smoke.py`: 14 actual-page synthetic cases, including saved/reloaded blank Price, blocked submissions, legacy edit fidelity and preview/CSV/XLSX equality. |
| T8 | commit containing this report | `DELIVERY_RUNTIME_DIFF_20261030.json`, `docs/DEPLOYMENT_CHECKLIST_20261030.md`, `docs/HANDOVER_DRAFT_20261030.md`, this report: current hashes, every changed runtime reason and full-suite instructions. |

## T1: individual baseline failure decisions

Baseline full run: **5 failed, 1103 passed, 1 skipped, 30 warnings in 224.65s**.
The five failures match the review. Each is a stale test expectation, not a
reason to restore a certified stock or capacity formula.

| Failing test | Decision / retained protection |
|---|---|
| `test_current_zero_sets_known_quantity_and_retry_is_exactly_once[False]` | Stored zero and known recorded total remain 0; `current_occupancy` stays None. Existing exactly-once transaction/revision/audit assertions retained. |
| `test_current_zero_sets_known_quantity_and_retry_is_exactly_once[True]` | Same distinction when the prior quantity is unknown. Zero establishes a recorded zero, not verified occupancy. |
| `test_zero_count_ui_save_refresh_and_account_summary` | Assert `Recorded Bird Count total`, `Usage percentage: Not established`; keep zero export and no lifecycle mutation checks, and explicitly recheck one revision/audit after viewing. |
| `test_quota_presentation_distinguishes_two_unknown_definitions` | Usage label is `Not established`; both independent missing definitions remain visible. |
| `test_usage_fresh_shared_context_does_not_invent_a_formula` | Recorded total is 10 while occupancy remains None; keep Account scope, two Flocks and two transactions checks. |

## Reproducible offline verification

Run from the release directory. Executable below is the existing project venv;
on another offline-equipped machine use its Python 3.12 environment and the
review dependencies. Network is blocked by the existing test harness.

```powershell
& '../../.venv/Scripts/python.exe' -m pytest -q
& '../../.venv/Scripts/python.exe' scripts/check_snowflake_readiness.py
git diff --check
```

| Exact pytest arguments after `python -m pytest` | Result |
|---|---|
| `tests/test_current_count_zero.py tests/test_spent_fowl_relationship.py::test_quota_presentation_distinguishes_two_unknown_definitions tests/test_staff_workflows.py::test_usage_fresh_shared_context_does_not_invent_a_formula -q` | 19 passed in 16.15s |
| `tests/test_r2_rules_loading.py tests/test_quota_flock_position.py -q` | 40 passed in 2.51s |
| `tests/test_r2_calculation_guards.py tests/test_quota_position_ui.py -q` | 7 passed in 8.72s |
| `tests/test_r2_daily_quota_parity.py tests/test_operational_flock_quota_import.py tests/test_adjustment_signed_entry.py -q` | 63 passed, 3 warnings in 12.49s |
| `tests/test_r2_usability.py tests/test_r2_calculation_guards.py tests/test_quota_position_ui.py tests/test_staff_workflow_ui.py -q` | 10 passed in 14.67s |
| `tests/test_quota_reconciliation_sql.py -q` | 2 passed in 0.04s |
| `tests/test_delivery_smoke.py -q` | 14 passed in 16.23s |
| `-q` (FULL final suite) | **1160 passed, 1 skipped, 31 warnings in 239.63s (3m59s); 0 failed** |

Readiness: passed. Final `git diff --check`: passed (no whitespace errors).
Protected-file verification: 20 protected runtime files have no Git diff against 8985521 and identical repository blob bytes; working checkout uses pre-existing LF/CRLF variants (11 differ from the LF blob only in line endings). No protected working file was rewritten.

The original suite has one pre-existing environment-dependent installer test
skip because the required private fresh-install evidence is not in this release.
No skip/xfail was added or safety assertion removed to obtain a passing run.
The final full-suite summary reports this skip explicitly. The 31 warnings include existing pandas dtype/concatenation warnings and a timestamp conversion warning; a passing offline run does not certify real-engine timestamp behavior.

New T4 fixtures initially made two incorrect assumptions about the frozen file
contract: literal CSV NaN is parsed as missing Price, and blank UPDATE fields
preserve stored values. Those contracts were not changed. Tests now assert that
behavior explicitly; invalid nonfinite CSV Price uses Infinity, and the missing
counterparty UPDATE changes an unlinked Adjustment into Purchase. Direct commit
NaN rejection, rejected-write rollback and unchanged-history checks remain.
T5's first fixture exposed normalized ID casing; the fallback now displays the
actual source ID spelling when no Account name exists.

## Runtime package and protected boundaries

Saved deployment baseline: **89 runtime files**; candidate: **94 artifacts**; **14 modified, 5 new, 0 deleted** against that saved baseline. All 19 change reasons and current LF-normalized hashes match the checklist. No fresh live comparison is claimed.
The saved manifest is not a new live snapshot. Authentication seeds and the
existing deployment variant are preserved; no sharing-copy auth is imported.
`config/quota_rules.json` remains an explicit artifact. No database, warehouse,
entry point, role, grant or connection setting changes are needed by these fixes.

The daily file reader, alias parsing, row identity and normalization contracts
are unchanged. T4 adds validation after merging an UPDATE with its stored record;
only relevant changed business fields are revalidated. Historical unchanged
labels, values, Price NULL/0 and credit labels remain unchanged.

Before any separately authorized release, obtain a current live drift snapshot
and rollback source/grants, compare to this exact candidate and follow the
checklist. Do not run migration, SQL08/SQL18, source supplements or date repair
as part of deploying this UI/validation change. Company-engine commit/rollback,
concurrency and employee-browser checks remain to verify.

## Staff decisions still open

- Confirm current-stock lifecycle inclusion, source priority for same-day Count
  observations, completeness and units; recorded Bird Count is not occupancy.
- Confirm quota opening evidence, units, lease inclusion/expiry and same-day
  snapshot ordering before certifying current usable quota or percentages.
- Confirm provisional daily type/counterparty policy and the intended Base-entry
  workflow. These fixes do not expand new-entry transaction choices.
- Missing/inactive source evidence and existing historical relationship holds
  remain unresolved; no inferred relationship or business record was written.

## Git delivery

Only `delivery-candidate-r2-20261030` is authorized for normal push to
`https://github.com/vencentgreat-cmyk/efns-prototype.git`. No force, other branch
push, main merge, history rewrite or repository-setting change is permitted.
The remote hash must equal the commit containing this report; the exact hash is
printed after push using `git ls-remote origin delivery-candidate-r2-20261030`.
A commit cannot embed its own hash; use that command and the final delivery
message for the independently checked remote SHA.
