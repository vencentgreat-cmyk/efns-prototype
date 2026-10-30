# Delivery report — 30 October 2026

## Outcome and scope

Prepared locally on `delivery-candidate-20261030`, from
`daily-entry-fixes-20261030` at `24f20478cf688a73547570d6fec3e1f7fafa9ad4`.
Nothing was pushed or deployed. No Snowflake connection, company script,
company data/permission/schema change, web search or real CSV analysis occurred.
All edits are under `releases/employee_trial_2026_10_29`. Existing documents
were read only where edited (the handover); no other design/evidence review
was started. Calculations and units remain PENDING/Not established.

## Local commits and files by task

### T1: `d2ca71630dacc6602aa98045d339ed88cc6a6af5`

Align quota type choices and preserve legacy label compatibility

`app/pages/4_Reports.py`; `app/services/quota_usage.py`; `app/services/report_center.py`; `data/constants.py`; `data/flock_quota_import.py`; `data/quota_types.py`; `data/record_safety.py`; `data/repositories/mock.py`; `data/repositories/snowflake.py`; `data/validation.py`; `tests/test_account_usage_quantity.py`; `tests/test_delivery_quota_types.py`

### T2: `43b3eb53185012c9a507f3090e289dcc12a5b763`

Use current quota activity choices with legacy lease compatibility

`app/pages/8_Quota_Transactions.py`; `data/constants.py`; `data/validation.py`; `tests/test_daily_quota_entry.py`; `tests/test_delivery_transaction_choices.py`

### T3: `7eddcb2e0f6efd8dc505da62850a6c6bfc3ab54f`

Apply latest Base snapshots and zero-effect closure in PENDING draft

`config/quota_rules.json`; `data/quota_position.py`; `tests/test_delivery_base_snapshots.py`; `tests/test_quota_flock_position.py`

### T4: `30c3dacb2a2630e18fdce5a72c51fb1af0eb8e55`

Guard English-only app and data source text

`tests/test_delivery_english_ui.py`

### T5: `6b582ddde731fc250f4353bcb02110215762315c`

Record confirmed business findings and remaining data issues

`docs/HANDOVER_DRAFT_20261030.md`

### T6: `5fc849aed70211cd05914b0025a4e11d99602b96`

Prepare complete runtime delta and staff smoke checklist

`DELIVERY_RUNTIME_DIFF_20261030.json`; `docs/DEPLOYMENT_CHECKLIST_20261030.md`; `snowflake.yml`

### T7: final verification commit

The local commit containing this report is the T7 commit (`HEAD` on completion;
obtain its exact ID with `git log -1 --format=%H`). Files:
`tests/test_delivery_package_guards.py`, `data/quota_position.py`,
`DELIVERY_RUNTIME_DIFF_20261030.json`, `docs/DELIVERY_REPORT_20261030.md`.
It preserves the failing unknown-type regression, fixes that guard and refreshes
only the affected candidate hash. A report cannot embed its own content-derived
commit hash without changing it.

## Implemented behavior

- **T1:** New quota choices use the three exact supplied names. The two former
  spellings remain supported in validation, parameterized read filters, edit
  controls and view-only grouping. Account usage combines compatible aliases
  without rewriting records. Daily parsing/identity/normalization is unchanged:
  only two membership checks in `validate_flock_quota_batch` changed.
- **T2:** New transaction choices are Adjustment, Purchase, Sale, Lease (In),
  Lease (Out), Base, marked "confirmed from usage data 2026-10-30; provisional
  until staff confirm". Legacy lease inputs and unchanged historical edits
  remain supported. Historical Global Adjustment/Terminate remain reportable,
  not new-entry choices. Counterparty requirements are unchanged.
- **T3:** The PENDING draft selects the latest Base separately per registration
  and as-of date, reports excluded older Bases and activity absorbed by the
  restatement, and avoids deducting the same pre-snapshot sale twice. Terminate
  Quota 0 records a zero-effect closure in the returned draft only; no database
  registration is closed or zeroed. Global Adjustment is positive. Ambiguous
  same-day snapshots, active leases crossing snapshots, inconsistent closed
  balances and post-closure activity block a position rather than being guessed.
  Unknown types, source gaps, state and unit protections remain. Stock draft is
  untouched; no percentage was enabled.
- **T4:** App/data text scan found no Han/CJK text, so no protected source needed
  a wording change. A permanent scan regression was added.
- **T5:** Handover now records supplied F1–F10, corrects the Base and initial-flag
  interpretation, and separates confirmed old-system facts from current stock
  certification. Meisners, Carbon Dioxide and Windy Bay remain documented issues.
- **T6:** Saved-baseline comparison is complete: 89 baseline runtime files,
  94 candidate artifacts, **13 modified + 5 new + 0 deleted**. Every difference
  and reason is listed in `docs/DEPLOYMENT_CHECKLIST_20261030.md`, with hashes in
  `DELIVERY_RUNTIME_DIFF_20261030.json`. This compares saved deployment evidence,
  not freshly queried live state. `snowflake.yml` now includes the required
  `config/quota_rules.json`; target/runtime/entry/warehouse/grants are unchanged.
  The checklist supplies 15 proposed browser smoke steps, not completed UAT.

## Exact commands and results

Run from `releases/employee_trial_2026_10_29`, using the existing Windows venv.
Final per-task runs (overlap the final combined total):

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_delivery_quota_types.py -q
# 10 passed in 5.83s
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_delivery_transaction_choices.py tests/test_daily_quota_entry.py tests/test_daily_entry_boundaries.py -q
# 48 passed in 23.63s
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_delivery_base_snapshots.py tests/test_quota_flock_position.py tests/test_quota_position_ui.py -q
# 44 passed in 7.07s
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_delivery_english_ui.py -q
# 1 passed in 0.88s
```

Final combined run includes all requested suites, all new delivery tests and
additional operational-import coverage:

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_controlled_execution.py tests/test_source_field_fixes.py tests/test_account_usage_quantity.py tests/test_staff_workflow_ui.py tests/test_report_nullable_sum.py tests/test_flock_report_record_count.py tests/test_quota_flock_position.py tests/test_quota_position_ui.py tests/test_quota_reconciliation_sql.py tests/test_daily_quota_entry.py tests/test_historical_transaction_reports.py tests/test_daily_entry_boundaries.py tests/test_report_center.py tests/test_delivery_quota_types.py tests/test_delivery_transaction_choices.py tests/test_delivery_base_snapshots.py tests/test_delivery_english_ui.py tests/test_delivery_package_guards.py tests/test_operational_flock_quota_import.py -q
# 244 passed in 116.04s (0:01:56); 0 failed, 0 skipped, 0 xfailed
& '..\..\.venv\Scripts\python.exe' scripts/check_snowflake_readiness.py
# Snowflake readiness checks passed — offline/static.
git diff --check
# Exit 0; each staged commit also passed whitespace checks.
```

Local AppTest, Mock commits and fake SQL capture are not native Snowflake or
company-browser evidence. No existing failing assertion was deleted or marked
xfail. One prior test now expects the canonical grouped label rather than the
old constant spelling; another explicitly selects Purchase rather than relying
on the former default. Fixtures put Base before subsequent activity so a
same-day ordering ambiguity cannot be accidentally treated as known.

## Failures found and stopped/deferred work

Nothing remains failing; no task was abandoned. Initial failures are retained
in ignored local logs:

- T1 initial run (including quantity regression): 1 failed / 28 passed because
  the new AppTest used the wrong save-button key. Correcting the test selector
  produced the passing result above; production behavior was not weakened.
- T7 initial package guards: 1 failed / 2 passed. This was a real new draft
  defect: a later Base could hide an earlier unknown transaction type. The
  regression remains and the draft now blocks that type before snapshot
  absorption. The final 244-test run includes it.
- The first CJK grep used an unsupported Unicode property name. The corrected
  Han grep found no matches, and the broader automated scan passed.

Protected-file checks against the starting commit confirmed 20 files unchanged,
including connection/authentication/navigation, migrations and frozen mappings,
read-only reconciliation SQL, date repair, supplements, continuity and the stock
function. Every non-validator function in `data/flock_quota_import.py` is AST-
identical to the start. Existing package settings/grants are identical except
for the added rules artifact. Runtime diff hashes match the final local files.
Logs are private/ignored `.local/delivery_*`; no business fixtures or credentials
were added. Current live drift, permissions, engine behavior, final-runtime R4
probe and browser UAT are **to verify**, not a deployment claim.

## Staff decisions / follow-up

1. Approve the provisional entry/credit lists and signed/zero Adjustment entry
   policy. The existing positive-only daily quantity rule was deliberately not
   broadened by a task that specifies choices, not new numeric policy.
2. Define how "Base only for new registrations" is recognized/enforced. Confirm
   same-day activity ordering and whether an overlapping lease is included in
   a restated Base. The draft holds ambiguity rather than making that decision.
3. Confirm quota units/opening completeness, Windy Bay's one-day `6/1/2026` lease
   interpretation, current/live flock scope and count-source priority. Old rollup
   agreement does not certify present occupancy; Inactive/source gaps still block.
4. Recover real Registration GUIDs for the 21 Meisners transactions; do not guess
   links. Carbon Dioxide's Account/reference modeling and 71 reported links remain
   out of scope, with no cleanup or reclassification.
5. Separately authorize any engine/browser validation or release. Existing frozen
   reconciliation SQL still contains the superseded additive Base candidate;
   it is diagnostic only and needs a separately authorized update. This task
   expressly did not edit it or rerun any migration/date/Spent/supplement scope.

See the updated handover and deployment checklist for orientation and proposed
employee tests. No human question, external operation or push was initiated.
