# Independent review guide

## Start with the facts, then challenge them

`review/BASELINE.json` identifies the frozen candidate; `SOURCE_ORIGINS.json`
records the file-level origin/hash. `CANDIDATE_CONSISTENCY.json` checks every
candidate artifact, including configuration and the deployment descriptor.
The sole sharing exception is four disabled prototype seed hash literals in
`app/security.py`; the deployed candidate is untouched. No safety/identity or
business logic is redacted. Review harness files are additional context.

The candidate has 14 modified and2 added runtime files relative to its saved
live baseline. The zero-count revision changes only `data/validation.py`,
`data/flock_quantity.py`, `app/pages/6_Flock_Transactions.py` relative to the
previous business candidate. See `review/CHANGE_SCOPE.md`. The prior working
tree's older date modules were not used. No company query evidence or old Git
history is included, so do not infer current deployment or actual DB contents.

## Review targets and code entry points

| Concern | Start here | Tests / questions |
|---|---|---|
| Current bird observation versus ordinary activity | `data/flock_quantity.py`, page6, `data/validation.py` | `test_current_count_zero`, `test_account_usage_quantity`, `test_staff_workflows`; 10→0, unknown→0, no lifecycle side effects, Removal bounds |
| Transaction ownership, CAS, replay | `data/connection.py`, `data/repositories/continuity.py`, `snowflake.py` | `test_connection`, `test_optimistic_locking`, quantity tests; inspect actual statements, request reuse, two sessions versus one process |
| Revision and audit atomicity | `app/services/authorized_repository.py`, `data/flock_quantity.py`, continuity | Inject write/audit failure; verify same-transaction behavior and error preservation; fake executors cannot prove real engine isolation |
| Relationships and roles | `data/validation.py`, entity writers, auth/security | Facility/Flock Account consistency; Producer, test and counterparty Account roles differ; do not impose all-account equality |
| Imports and source retention | importing/intake, operational import, migration, historical corrections | `test_operational_review_persistence`, `test_manual_historical_corrections`, `test_continuity`, `test_v6_consistency`; reject/unsupported retained, preview versus commit, matching/retry and original bytes |
| Source identity | `data/migration_identity.py`, `source_trace.py`, `source_scope.py` | `test_migration_identity`, `test_source_history_trace`; batch+RAW identity, rejected/no-map rows retained, no fan-out |
| NULL/zero, count and export | `report_center.py`, `report_builder.py`, page4, `quota_usage.py` | nullable-sum/count/provenance/report-role tests; same preview/CSV/XLSX; duplicate joins, real0 and missing data |
| Restricted repairs kept intact | flock_date_repair/supplement and workspaces | batching/repair/supplement tests; full target set, guards, rollback, no trusted previews, preserve old receipts |
| Security | authorized wrapper, local versus Snowflake auth | permission tests include denial and injected actor; distinguish UI checks, repository checks and DB grants |

Names above omit the `tests/` prefix and `.py` for compactness. Inspect all
included tests and helpers; do not review only the table or previous pass counts.

## Minimal workflows to reproduce locally

1. Run `test_staff_workflows.py` and `test_staff_workflow_ui.py`: Account →
   Facility → Flock → activity, production matching/revision, Salmonella edit
   and report; validate wrong relations and read-only denials.
2. Run `test_current_count_zero.py test_account_usage_quantity.py`: confirmed
   Count/Removal,0/unknown/partial/all removal, multi-Flock totals, failures,
   stale versions, replay, mock concurrency, exported0. Check ordinary activity
   is not replayed into inventory. Quantity baseline assumptions are explicit.
3. Run report tests: missing Import Batch, producer role independence,
   nullable sums, Facility provenance, record count, filter/export agreement.
4. Run import/correction/date tests: invalid and rejected rows retain source,
   source identities do not cross batches, failed writes roll back, no inferred
   historical ownership, safe repair/reversal and batching statement counts.

Use `python -m pytest -q --tb=short` for the full *included* offline suite.
One snapshot-dependent test is skipped rather than supplied fabricated evidence.
Offline readiness is static artifact/SQL/source checking, not an online grant
or deployment verification. No SQL files should be executed for this review.

## Limits worth independent scrutiny

- Standard Snowflake PK/UNIQUE/FK declarations are not all enforced like local
  relational constraints. Examine transaction locks, affected-row accounting,
  target uniqueness and request handling; thread tests alone do not prove
  multiple-process/multiple-session safety.
- Current observations are restricted to Halifax today; historical activity
  does not automatically rewrite current birds. Ordinary edit/delete of a
  quantity-applied transaction is protected; a comprehensive event undo flow
  is not delivered by this candidate.
- Quota capacity units and transaction-direction formulas are not established;
  no usable real percentage is certified. Unknown counts cannot prove complete
  reporting, correct source units or absent unreported records.
- Existing mixed DEV provenance is retained in runtime configuration; no cloud
  data is present to certify scope labels, totals, all pending issues or grants.
- Dates and optional references must stay faithful to source. No automatic
  cross-Account foster approval, lifecycle inference or reconstructed history.

## Requested reviewer output

For each finding give severity, concrete file/function/line, reproducible
synthetic case, actual/expected behavior, risk and the smallest repair. Separate
confirmed defects, untested risks and missing business rules. Do not guess
quota units or historical relationships, expand scope or suggest deleting RAW.
State which tests actually ran and what a fake executor cannot demonstrate.
