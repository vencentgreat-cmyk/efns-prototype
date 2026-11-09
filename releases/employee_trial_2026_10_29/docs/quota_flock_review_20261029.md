# Local RAW review evidence and implementation — 2026-10-29/30

## Evidence boundary

Three user-exported aggregate CSVs were read completely from Downloads. They
were not copied into this repository. No Snowflake connection/query, deployment,
write, migration, archive or correction was performed in this task. Export
filenames describe capture time; original query SQL/Query IDs are not contained
in these CSVs. They do not establish a new query time or a per-GUID CORE gap.

| File | Data rows | SHA-256 |
|---|---:|---|
| Untitled 3_2026-10-29-2344.csv | 11 | 229d0bb1a862600f82f31b5c39d5623ab24e8c0760cb3ffa4c3bb48aa00cdb0b |
| Untitled 3_2026-10-29-2342.csv | 16 | 7f6a3ac0ee3388f445ebcdc3a90bb373158d95cac721c4a952ab82d875e298c2 |
| Untitled 3_2026-10-29-2344 (1).csv | 76 | 7b18e3cb66902bf338418de88c9c81bf36a0e645d3543d670c2a328267f5cb6d |

## Facts supported by the supplied aggregates

- Flock transaction aggregate: 15,520 source rows: Count 12,653; Delivery 2,588;
  Removal 265; Sale 14. Add/removal is only NULL (12,000) or N/A (3,520), so it
  supplies no usable direction. Count observations are never added to stock.
- Across **all** these transaction types, counter labels are Producer 11,156,
  Board 1,673, EFC/CEMA 815, NULL 1,876. For **Count only**, Producer is 10,156,
  Board 1,673, EFC/CEMA 815, NULL 9: 1,000 Producer labels belong to Delivery.
  A source-priority business rule cannot be inferred from these frequencies.
- Quota aggregate: 1,394 source rows, Yes 871 / No 523. All Yes reserve fields
  are absent; No reserve is 0. No-cohort Purchase and Sale each total 336,979;
  Lease (In) and Lease (Out) each total 87,651. These are balancing aggregate
  observations, not a per-owner completeness or business-direction proof.
- National Allocation: 1 / 746,357; Provincial Allocation: 16 / 12,733,996.
  They are excluded from Account entitlement and QUOTA_TRANSACTION import by
  the user's explicit scope instruction. Their broader series meaning remains
  a confirmation question; they are not silently attributed to an owner.
- State aggregate: quota transactions 1,381 Active / 13 Inactive; flock
  transactions 15,485 Active / 35 Inactive; quota registrations 61 / 30.
  Flock record state is 2,186 Active / 30 Inactive, with identical Status Reason
  totals. Permit Active is Yes 404 / No 21 / missing 1,791. These do not define
  lifecycle. Rollup state is 1 on all 2,216 source Flocks, not proof of a formula.

## Claims that still require row-level output

These CSVs do not contain target GUIDs, linked-transaction pairs, per-owner
missing rows, exact latest Count dates, end dates, or source rollup quantities.
The reported missing Sale/Lease Out/Base/Global Adjustment/Adjustment counts,
30/14 linked-pair details, proposed cohort history and effect on specific owners
are user-supplied investigation findings, not independently proven by these
aggregate attachments. No precise owner is inferred from a counterparty/name.
A plausible explanation is not confirmation of usable quota or current stock.

## Local changes (not deployed)

- Pure data/quota_position.py computes owner/type components and only releases
  net_position after explicit CONFIRMED rules plus verified source/state
  coverage. Missing rows return "N source rows not in CORE". Inactive rows are
  excluded AND block certification; unknown/unresolved Owner, duplicate IDs,
  invalid dates/quantities and unsupported types also block. Related Account
  does not increase Owner position. Paired transactions are not counted twice
  for the same account. Allocation totals never become entitlement.
- Pure data/flock_stock.py keeps stored Bird Count, old-system rollup reference,
  dated latest Count observations and later type-directed changes separate.
  Same-day multi-source observations remain conflicts (even equal numbers).
  No additive Count, inferred end, priority rule or state/date clearing exists.
  Explicit reviewed live scope is required in addition to CONFIRMED rules.
- config/quota_rules.json remains PENDING, including flock_stock. It contains
  candidate signs/inclusive lease rule for review, not approved formulas.
- quota_usage shows components and English limitations. The live UI has no
  verified RAW completeness/state adapter in this change, so it cannot claim
  an owner-specific missing-row count from CORE or calculate a position. Merely
  flipping CONFIRMED cannot expose a percentage: current stock, source/state
  verification and unit compatibility must also be provided. No registered
  Bird Count aggregate is passed off as current occupancy.
- Quota Transactions filters use actual distinct historical types; new-entry
  constants/validation are unchanged. The mixed "Filtered quantity" metric is
  removed. Owner/type recorded quantities preserve NULL and 0. Credit Type is
  only a UI relabel of QUOTA_LEASE_TYPE, without schema/data changes.
- Flocks shows latest dated Count observations/source labels next to stored
  Bird Count, flags source conflicts, and never writes a value when viewing.
- Migration normalization/new-package validation now keep National/Provincial
  Allocation RAW-only even when a parent is supplied. Frozen mapping JSON and
  stored RAW/NORMALIZED/batches are unchanged. Historical correction rebuild
  reuses the normalization guard. Ordinary new-entry choices are not expanded.

## Next manual SQL (read-only, not executed here)

Open sql/review/quota_flock_reconciliation_20261029.sql in a company Worksheet,
choose EFNS_DEV in the database selector and an already authorized read role.
Run identity first and stop on any company mismatch. Then execute T1e details,
T1e summary and identity guard before interpreting any account position. Save
those outputs privately, with query IDs/time. An unresolved-owner bucket must
remain unresolved; never assign it to Related Account. Allocation exclusions
are shown separately from account gaps.

Continue T1a full comparisons / match bands / 20 example IDs, T1b Deliveries,
T1c components, T1d termination and T1f Inactive rows. Source dates use the date
part without timezone conversion. Each statement scopes the original batch;
mapping joins use batch AND RAW-row identity, and left joins retain rejection
and no-target cases. Candidate arithmetic is labelled UNCONFIRMED. CORE-side
components exclude known RAW-Inactive rows; the SQL never returns a certified
net position. Missing owner/type rows are not dropped from the gap report.

SQL has offline SELECT-only/identity/section contract checks, but has NOT been
compiled/executed by Snowflake. Review outputs before accepting any source
completeness. All proposed signs, Base/snapshot interpretation, lease expiry,
Global Adjustment meaning, live scope, count priority and unit compatibility
remain business questions; use docs/quota_rules_confirmation_20261029.md.

References used for existing APIs/SQL NULL-count handling:
[Streamlit dataframe](https://docs.streamlit.io/develop/api-reference/data/st.dataframe),
[Snowflake COUNT_IF](https://docs.snowflake.com/en/sql-reference/functions/count_if).
COUNT_IF is coalesced only for record counts; unknown quantity SUM is never
filled with zero. This does not authorize any company action or Git push.

## Actual local validation

Final command, run from releases/employee_trial_2026_10_29 with the root
project virtual environment (Windows Python, forced Mock and network block):

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_quota_flock_position.py tests/test_quota_position_ui.py tests/test_quota_reconciliation_sql.py tests/test_controlled_execution.py tests/test_source_field_fixes.py tests/test_account_usage_quantity.py tests/test_staff_workflow_ui.py tests/test_report_nullable_sum.py tests/test_flock_report_record_count.py -q
& '..\..\.venv\Scripts\python.exe' scripts/check_snowflake_readiness.py
```

Result: **143 passed in 94.15s**, plus offline readiness passed. This includes
the original six guide suites and new pure-function, SQL-contract and actual
local AppTest cases. No xfail, removed regression or company data fixtures were
used. An earlier new AppTest failed only because direct Python dictionary
comparison treats NaN != NaN; it was corrected to compare the complete before/
after Mock Flock DataFrame, preserving the no-write assertion. The subsequent
final run passed. A later SQL-only summary/identity display refinement is
covered by a final rerun of its two static contract checks (not engine proof).

The saved live baseline manifest remains immutable capture evidence, not a
claim that this modified tree is deployed. QUOTA_FLOCK_PATCH_MANIFEST.json
lists the local changes/additions and protects prior runtime hashes. Original
authentication, R1/date repairs, navigation, supplements, source tracing,
permissions and new-entry type constants are unchanged. No root application
files were copied into this release and no original private attachments were
added. Company owner-level coverage, SQL engine syntax/results, new browser
rendering/export acceptance and staff interpretation remain unverified.
