# EFNS handover draft

30 October 2026. Local candidate only. No company connection, deployment or data
write was performed in this delivery task. This handover was read for editing;
other existing documents were not reread. Company
data totals, employee permissions and this candidate's browser acceptance are
**to verify**; offline tests are not evidence of those outcomes.

## 1. Purpose and pages

EFNS stores linked operational records, preserves source evidence and changes,
and provides permission-controlled queries and exports.

| Page | Purpose |
|---|---|
| Dashboard | Starting overview and module links. |
| Production Import | Upload and review production workbooks before business submission. |
| Production Data | Find, add and correct current production records. |
| Accounts & Facilities | Maintain Accounts and follow their linked business records. |
| Farm Locations / Facilities / Facility Details | Maintain location/building records and their parent links. |
| Flocks | Maintain flock registrations, relationships and recorded Bird Count. |
| Flock Transactions | Record activity; explicitly confirmed current Count/Removal is a separate operation. |
| Quota Registrations | Maintain quota identities and ownership, not a verified capacity balance. |
| Quota Transactions | Maintain activity, Price and counterparties; no certified available quota. |
| Daily Flock & Quota Import | Preview and submit supported daily CREATE/UPDATE rows. |
| Salmonella Tests / Salmonella Test Report | Maintain linked tests and query their reports. |
| Report Center | Filter, group and export selected records; stored type labels are not limited to new-entry choices. |
| Record Review & History | Inspect revisions, matching decisions and original-file/source tracking. |
| Migration Import | Restricted historical preparation, rejection review and separate correction/supplement workflows. |
| EIMS Reference Data | Inspect supported reference records. |
| System Status / Source Data Profiler | Diagnose configuration and source contracts; access depends on role. |
| Audit Log / User Management | Authorized administration of audit history and application access. |

An Account can have multiple Facilities/Flocks. A Flock has one optional current
Facility reference; multiple Flocks can share a Facility. A Quota Registration
belongs to an Account. Quota Transaction Owner is distinct from Related Account.
Production remains attributed to its recorded Producer, not the Facility owner.

## 2. Where things live

Use `releases/employee_trial_2026_10_29`, not the root development application.
The root `streamlit_app.py` **inside this release** runs `app/Home.py`; pages are
under `app/pages`. Do not copy older root modules over this candidate.

| File / directory | Responsibility |
|---|---|
| `data/connection.py` | Connector/Snowpark executors, binding, transactions and bounded lock acquisition. |
| `data/repositories/base.py`, `mock.py`, `snowflake.py` | Repository contract, synthetic local data and Snowflake access. |
| `data/repositories/continuity.py` | Source preservation, retained rows, revisions and shared transaction support. |
| `data/record_safety.py` | Create-once requests, protected corrections/deletions and history/audit. |
| `app/services/form_safety.py` | Reviewed form snapshots, unchanged-value preservation and request lifecycle. |
| `app/services/quota_usage.py` | Historical/registered Bird Count summaries and guarded, unestablished usage display. |
| `app/services/report_center.py`, `report_builder.py` | Curated datasets/aggregation/exports and the older joined-field selector. |
| `data/validation.py` | Daily rules, including the provisional counterparty requirement and optional Price. |

SQL is maintenance code, not a startup command. Conceptual dependencies are:
foundation/database/schemas (`00`, `01`), base CORE/production/security objects
(`02`, `03`, `05`), reviewed additive historical upgrades (`10`–`19`), compatible
reporting views (`04`), and exact authorized role/application grants (`06`, `08`).
Some scripts overlap; **this is not an instruction to run all files in numeric
order**. Select the approved fresh-install or upgrade procedure after checking
actual metadata and saved state. `09` is synthetic seeding, not real business
loading. Never casually replay migration, correction, supplement or date-repair
scripts. No SQL is authorized by this handover.

## 3. Offline testing

From this release directory in the existing Windows project environment:

```powershell
& '..\..\.venv\Scripts\python.exe' -m pytest tests/test_controlled_execution.py tests/test_source_field_fixes.py tests/test_account_usage_quantity.py tests/test_staff_workflow_ui.py tests/test_report_nullable_sum.py tests/test_flock_report_record_count.py tests/test_quota_flock_position.py tests/test_quota_position_ui.py tests/test_quota_reconciliation_sql.py tests/test_daily_quota_entry.py tests/test_historical_transaction_reports.py tests/test_daily_entry_boundaries.py tests/test_report_center.py -q
& '..\..\.venv\Scripts\python.exe' scripts/check_snowflake_readiness.py
git diff --check
```

On another machine, create/activate a Python 3.12 virtual environment, install
`requirements-review.txt`, and replace the executable prefix above with `python`.
No company credentials are required. `conftest.py` forces Mock/local settings
and blocks network. Tests and AppTest use synthetic records. Fake SQL capture
checks parameters, not real database transactions. Readiness is static/offline.
Company scripts, SQL installers, staging/archive operations and migration or
correction actions must not be used as an offline test command.

## 4. Data status and known gaps

Historical import retains original files/RAW, validation outcomes and source-to-
target mapping. Original rejections are not rewritten when a separate correction
succeeds. A retained or proposed target ID alone does not prove a CORE record
exists. Supplements are separate reviewed operations, not a full-batch replay.
Earlier approved date/link/source-label work must not be repeated for testing.
Exact committed/pending counts in the company database are **to verify** here.

Pending/rejected and missing-CORE rows still matter. An unknown Owner must not be
guessed from a counterparty or a display name. RAW Inactive transactions are
excluded from candidate calculations and block certified results until their
business meaning is confirmed. Allocation rows are retained RAW-only and are
not Account entitlement or QUOTA_TRANSACTION import candidates.

Use the manually executed, read-only
[reconciliation SQL](../sql/review/quota_flock_reconciliation_20261029.sql): identity
first, then T1e missing-target details/summary and uniqueness checks. Remaining
sections compare observations, deliveries, components and Inactive source rows.
SQL engine syntax/results are **to verify**; this task did not run it. Its
unchanged additive Base candidate is superseded by the confirmed latest-Base
snapshot rule. Use the file for source/link reconciliation, not a valid account
position. A separately authorized follow-up must update that candidate SQL; this
task expressly prohibits editing it.

## 5. Deferred business and runtime work

- Current stock is not the historical Bird Count sum. Record Active/Inactive,
  Permit Active, disposal, Count source priority and effective-time rules need
  review. Count is an observation, never an addition. No end event or zeroing is
  inferred from a date/status.
- Base is confirmed to be a per-registration restating snapshot; Terminate
  Quota is a zero-effect closure, and historical Global Adjustment is a positive
  province-wide increase applied to producers. Quota units, complete opening
  evidence, lease expiry/inclusion and same-day snapshot ordering still need
  confirmation. These confirmed facts do not certify a complete position.
  `data/quota_position.py`, `data/flock_stock.py` and `config/quota_rules.json`
  contain the **PENDING** draft; do not switch it to CONFIRMED without evidence.
  Missing/inactive source coverage and unverified current stock independently
  block percentages. Use the [confirmation sheet](quota_rules_confirmation_20261029.md).
- New-entry choices are Adjustment, Purchase, Sale, Lease (In), Lease (Out),
  Base: confirmed from usage data 2026-10-30; provisional until staff confirm.
  Base is intended for new registrations; defining/enforcing that workflow
  boundary still needs a staff rule. Legacy lease labels remain compatible.
  Historical labels in report filters do not authorize creating those types.
  Related Account is provisionally required for Purchase/Sale and both lease
  label spellings, not every historical type.
- R4 lock-timeout runtime probe for the final candidate: **to verify / still to
  run as a separately authorized release check**. This run did not inspect or
  repeat prior isolated probe evidence and does not negate earlier results.
  Do not call local/fake-executor tests company-engine validation.

## Confirmed business facts (2026-10-30)

Source: user-provided old EIMS UI and read-only findings. These statements were
not independently queried or recalculated in this delivery task.

1. Since 2018, staff use Adjustment, Purchase, Sale and Lease (In)/(Out); Base is
   for new registrations. Global Adjustment and Terminate Quota are historical
   only in that period. National/Provincial Allocations remain province totals,
   RAW-only and excluded from Account entitlement.
2. Real quota types are Egg Production, Non Commercial Pullet Quota, Commercial
   Pullet Grower. Older constant spellings remain readable/editable. Filtering
   and grouping recognize their equivalence without rewriting stored labels.
3. Base is a snapshot, not an additive award: a later Base restates the total.
   Use only the latest dated Base per registration. Earlier quantities/activity
   already represented by that snapshot must not be counted again. Same-day
   ordering and overlapping leases remain guarded rather than guessed.
4. Terminate Quota with quantity 0 means the registration closed after its quota
   was sold/transferred. It has zero numeric effect; it does not manufacture a
   missing balancing sale or update database status from a draft calculation.
5. Global Adjustment is a positive province-wide increase applied to producers,
   used in 2004–2012. Later equivalent increases are entered as Adjustment.
6. Old Net Bird Count is Delivery minus Removal minus Sale. The user reports
   roughly 90% agreement for current flocks, with rollup lag (new flocks can show
   0). This is an old-system reference, not proof that all historical flocks are
   live, complete or suitable for current occupancy.
7. TransactionInitialFlag No marks bulk migration into Dataverse on 2018-05-16
   with EIMS IDs; Yes marks later staff-created rows. It is not a direction.
   Earlier reverse-cohort hypotheses are superseded by this finding.
8. The 21 T & P Meisners Poultry Farm Ltd. transactions had Registration links
   in the old UI, but export lost the links. Never guess or auto-fill them.
9. Carbon Dioxide exists as an active Account and 71 Flocks reference it as
   disposal plant/method. This task does not reclassify that Account or links.
10. Disposal Date may be a future planned disposal. It is not itself an error
    and must not automatically end or clear a Flock.

## Known data issues for later

- Meisners: recover the actual missing Registration GUIDs with source evidence;
  a displayed registration label or name is not an approved relationship.
- Carbon Dioxide: confirm reference-data versus Account modeling separately;
  do not remove or merge the current Account or the 71 reported links.
- Windy Bay: the one-day lease labelled `6/1/2026` awaits a staff answer. Confirm
  the date interpretation and effective/end-date treatment; no automatic fix.
- The existing positive-only daily Quota Count policy was not broadened here.
  Confirm signed/zero Adjustment entry behavior and how "new registration" is
  recognized before enforcing a stricter Base-entry workflow.

## 6. What to do if something fails

| Situation | Safe next action |
|---|---|
| “System busy” | Stop repeated clicks. Keep the draft/context. If the message explicitly confirms no write started, reload and review before one retry. Otherwise establish the outcome first. Ask a maintainer to inspect persistent contention; do not change timeouts casually. |
| “COMMIT outcome is unknown” | Do not save again, invent a new request or undo anything. Preserve the request/operation and record identifiers. An authorized maintainer must check the receipt, revisions/audit and current target through an independent read-only connection. |
| Correction/version conflict | Preserve the intended edits, reload current values, review differences and explicitly reconfirm. Never auto-refresh the approved version just to pass the check. |
| Referenced deletion is blocked | Leave the record intact and inspect the listed relationships. Do not force-delete parents, clear links or remove audit. Escalate business decisions about deactivation/retention. |

Normal reports read corrected current business values; revision history must
not be added as another business submission. Blank Price means unknown; explicit
0 is zero. Saved results, draft conflicts and audit warnings are distinct states.
