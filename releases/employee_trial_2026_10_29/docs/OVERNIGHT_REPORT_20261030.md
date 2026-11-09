# Overnight report — 30 October 2026

## Result and boundaries

Local work completed in `releases/employee_trial_2026_10_29` only. No Snowflake
connection, company script, deployment, migration/correction execution, web
search, CSV analysis, push or repository-setting change. Existing `docs/` files
were not read. The protected calculation drafts, rules, normalization/mapping,
reconciliation SQL, authentication, connections, date repair, supplements and
navigation remain unchanged after the Step 0 checkpoint. New-entry transaction
choices are unchanged. No business rule was declared confirmed.

## Branches and local commits

Starting branch: `codex/identity-history-archives`, HEAD `19a4a9c16503185294271a633ae72eb5459a5481`.

| Step | Branch | Commit / subject |
|---|---|---|
| 0 | `quota-flock-review-20261030` | `99f9b64998259293684b06a7f6c6d0a359413855` — Quota/flock review: activity-only UI fixes, PENDING calculation draft, read-only reconciliation SQL |
| 1 | `daily-entry-fixes-20261030` | `48e64b1a77d9d07de15ea640fd024cad33cd75aa` — Fix quota entry price, counterparty and decimal fidelity |
| 2 | `daily-entry-fixes-20261030` | `0fbd589d0deb3f6768c564206e599800c8cf07f7` — Expose historical transaction types and credit labels in reports |
| 3 | `daily-entry-fixes-20261030` | `c9e8154afbc8ef958dec220b58a46244e9dcc73d` — Test quota save bindings, validation and retry boundaries |
| 4 | `daily-entry-fixes-20261030` | The documentation commit containing this report (`HEAD` on completion) — Add employee handover and overnight verification report |

Step 0 preserved all 17 existing changed/new files as requested; no original
branch history was rewritten. Task 4 cannot embed its own commit hash without
changing that hash. Read its exact ID with `git log -1 --format=%H`.

## Files and outcomes per task

**Step 0 (preservation only):** `README.md`, `QUOTA_FLOCK_PATCH_MANIFEST.json`,
`app/pages/5_Flocks.py`, `app/pages/8_Quota_Transactions.py`,
`app/services/quota_usage.py`, `config/quota_rules.json`, `data/migration.py`,
`data/position_evidence.py`, `data/quota_position.py`, `data/flock_stock.py`,
`docs/quota_flock_review_20261029.md`, `docs/quota_rules_confirmation_20261029.md`,
`sql/review/quota_flock_reconciliation_20261029.sql`,
`tests/test_quota_flock_position.py`, `tests/test_quota_position_ui.py`,
`tests/test_quota_reconciliation_sql.py`, `tests/test_staff_workflow_ui.py`.

**Task 1:** `app/pages/8_Quota_Transactions.py`, `data/validation.py`,
`tests/test_daily_quota_entry.py`.

- New Price starts blank and saves unknown as None/SQL NULL; explicit 0 stays 0.
  Notes-only edits preserve the old value, including NULL/0. Explicit clearing
  and setting zero are tested. Invalid new Price is rejected.
- Counterparty requirement is shared by UI/validator and commented
  `provisional - confirm with business`: Purchase, Sale, both parenthesized lease
  labels and legacy Lease In/Out. Other types do not require a counterparty,
  but a supplied reference must exist. Unsupported new-entry types are still
  rejected; historical type retention is not permission to create them.
- Decimal Quota Count appears without integer rounding; whole values do not
  gain decimal places. List formatting is view-only, not a stored-value change.
- Stored legacy Credit Type is visible and preserved on edit. Existing
  unchanged historical fields are not forced through new-entry rules.

**Task 2:** `app/services/report_center.py`, `app/services/report_builder.py`,
`app/pages/4_Reports.py`, `tests/test_historical_transaction_reports.py`.

- Backend type filtering/grouping already accepts historical labels; no
  arithmetic rewrite was needed. Customize Report incorrectly used the daily
  constants, so its filter now uses actual stored transaction labels.
- Credit Type is available in Report Center and replaces the old display label
  in the legacy builder; database column names are unchanged.
- Tests compare grouped preview with CSV/XLSX for historical quota types and a
  synthetic non-constant Flock type, including exact four-place decimal values,
  NULL, zero and signed Adjustment. Dataset switching clears obsolete filters.
- The older builder only selects joined fields: it has no filter/group API or
  Flock Transaction dataset. Those operations are tested through Report Center;
  a new legacy-builder subsystem was not added.

**Task 3:** `tests/test_daily_entry_boundaries.py`.

- Adds captured native writer / Snowpark binding checks for NULL versus zero,
  invalid-input draft retention, identical retry after interrupted navigation,
  one creation/revision/audit, and refusal to clear a required counterparty.
- SQL capture is a synthetic executor, not a real Snowflake transaction test.
  AppTest is local page execution, not company-browser acceptance.

**Task 4:** `docs/HANDOVER_DRAFT_20261030.md`, this report.

Test logs and scope checks are in ignored release `.local/`; they are not
committed. No unrelated project files were copied or reformatted.

## Exact commands and actual results

Run from `releases/employee_trial_2026_10_29` using the existing Windows venv.
Individual commands (final runs; counts overlap the combined run):

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_daily_quota_entry.py -q
# 25 passed in 11.10s
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_historical_transaction_reports.py -q
# 10 passed in 6.70s
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_daily_entry_boundaries.py -q
# 5 passed in 6.87s
```

Final combined command includes the six requested existing suites, three
quota/flock draft suites, all new tests and an extra Report Center regression:

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_controlled_execution.py tests/test_source_field_fixes.py tests/test_account_usage_quantity.py tests/test_staff_workflow_ui.py tests/test_report_nullable_sum.py tests/test_flock_report_record_count.py tests/test_quota_flock_position.py tests/test_quota_position_ui.py tests/test_quota_reconciliation_sql.py tests/test_daily_quota_entry.py tests/test_historical_transaction_reports.py tests/test_daily_entry_boundaries.py tests/test_report_center.py -q
# 194 passed in 102.15s; 0 failed, 0 skipped, 0 xfailed
& '..\..\.venv\Scripts\python.exe' scripts/check_snowflake_readiness.py
# Snowflake readiness checks passed (offline/static).
git diff --check
# Exit 0. Staged whitespace checks also passed before each commit.
```

Git warned about future LF-to-CRLF conversion on some files; no whitespace-check
failure resulted. Protected-path comparisons use LF-normalized Git contents.

## Failures encountered and remaining limits

Nothing is left failing or xfailed, and no task was stopped. Early test runs
exposed test-harness issues that were corrected without changing business rules:

- Task 1 first run: 1 failed / 24 passed. Mock history represented unknown as
  NaN, so the null assertion was made null-aware; separate SQL-bind assertions
  still require actual None, not zero or the string "None".
- Task 2 first run: 4 failed / 6 passed, then 1 failed / 9 passed. Decimal/export
  checks now compare exact decimal values rather than Decimal-vs-binary-float
  object equality. The AppTest now waits for the real rerender after changing
  output columns before selecting grouping fields. No rounding tolerance or
  removed test hides a data difference.
- Task 3 first run: 1 failed / 4 passed. An import shadowed the AppTest variable;
  using an explicit module alias corrected the synthetic test.
- Local Streamlit skill discovery found a missing bundled SKILL.md. No web
  fallback was used, in accordance with the overnight restriction.

Company metadata, real browser appearance, native SQL execution/concurrency,
final-candidate R4 lock-timeout runtime probe, current data counts and employee
access rollout are **to verify**. Earlier probe/release evidence was not reread
or invalidated here. No deployment is implied by these local commits.

## Open human decisions

1. Confirm new-entry transaction/credit type choices and the provisional
   counterparty requirement; retain historical labels without inventing roles.
2. Confirm quota units, baseline date, Base versus snapshot meaning, adjustments,
   leases and termination before enabling an account position or percentage.
3. Confirm live-flock scope, Count-source priority, trusted reference count and
   the meaning of RAW Inactive transactions; missing-owner rows need evidence.
4. Authorize the separate final-candidate runtime probe/release process and
   browser acceptance before company use of the new local changes.

No question or company operation was issued overnight. See
[HANDOVER_DRAFT_20261030.md](HANDOVER_DRAFT_20261030.md) for page/file orientation
and safe responses to busy, unknown-commit, correction-conflict and referenced-
deletion messages.
