# Deployment checklist — 30 October 2026

**Preparation only; do not deploy from this checklist without separate approval.**
Work tree: `releases/employee_trial_2026_10_29`, branch `delivery-candidate-r2-20261030`.
Target declared by the existing package: `EFNS_DEV.APP.EFNS_INTERNAL_APP`, root
`streamlit_app.py`, `SYSTEM$WAREHOUSE_RUNTIME`, warehouse `EFNS_DEV_WH`.
Current live identity, drift, owner and grants are **to verify**; no company
connection or release was performed here.

## Complete saved-baseline runtime comparison

Source: immutable `RELEASE_SOURCE_MANIFEST.json`, not a fresh live download.
Hashes compare LF-normalized bytes as documented by that manifest. Private live
snapshots, credentials, real business exports and execution manifests are not
included. `DELIVERY_RUNTIME_DIFF_20261030.json` records before/after hashes.

Saved baseline: 89 runtime files. Candidate artifacts: 94. Changes: 14 modified, 5 new, 0 deleted.

| Runtime file | Status | Why |
|---|---|---|
| `app/pages/4_Reports.py` | MODIFIED | Historical type filters, record-count reporting preserved, canonical quota filters and Credit Type selection. |
| `app/pages/5_Flocks.py` | MODIFIED | Latest Count observations/conflicts; guarded draft failure; concise caption with details in calculation expander. Original navigation unchanged. |
| `app/pages/8_Quota_Transactions.py` | MODIFIED | Price NULL/0, signed Adjustment/decimal fidelity and legacy edits; guarded owner component table with Account names and ID fallback; concise activity-only caption. |
| `app/services/quota_usage.py` | MODIFIED | PENDING Account-wide recorded Bird Count and guarded draft calculation; current stock/percentage remain unestablished; detailed limitations moved into expander. |
| `app/services/report_builder.py` | MODIFIED | Credit Type display label in the older joined-field builder. |
| `app/services/report_center.py` | MODIFIED | Historical type options, Credit Type field and view-only alias-compatible quota grouping/filtering. |
| `config/quota_rules.json` | NEW | PENDING rules and user-supplied F3-F5 meanings, not calculation approval. |
| `data/constants.py` | MODIFIED | Three canonical quota types and six current transaction choices, plus legacy lease input compatibility. |
| `data/flock_quota_import.py` | MODIFIED | Two daily-validation membership checks accept the known quota aliases; parser/normalization/identity untouched. |
| `data/flock_stock.py` | NEW | Prior PENDING observation-only stock draft; unchanged by this delivery task. |
| `data/migration.py` | MODIFIED | PRE-EXISTING local RAW-only Allocation guard, frozen at delivery branch start; not modified by this task. |
| `data/operational_flock_quota_import.py` | MODIFIED | Daily quota preview uses shared changed-field validation; existing parsing, identity, normalization and blank UPDATE contracts preserved. |
| `data/position_evidence.py` | NEW | Prior pure null/date/GUID/state helpers used by the PENDING draft. |
| `data/quota_position.py` | NEW | PENDING owner component/latest-Base draft plus logged built-in PENDING fallback for missing/invalid rules. |
| `data/quota_types.py` | NEW | Read/comparison compatibility for canonical and legacy labels, without write-time relabeling. |
| `data/record_safety.py` | MODIFIED | Signed Adjustment corrections and type-only sign guard; unchanged historical values preserved, with existing CAS/transaction/audit protection retained. |
| `data/repositories/mock.py` | MODIFIED | Existing alias-compatible reads plus shared daily quota validation at commit, before writer, preserving rollback behavior. |
| `data/repositories/snowflake.py` | MODIFIED | Existing alias-compatible reads plus shared daily quota validation and unique parent checks inside existing commit transaction; no executor/transaction implementation change. |
| `data/validation.py` | MODIFIED | Shared finite signed nonzero Adjustment, optional Price/counterparty/date rules and changed-field daily quota review helper; historical unchanged values retained. |

Other packaging change: `snowflake.yml` now explicitly includes
`config/quota_rules.json`; without it `load_rules()` would fail in a CLI-created
package. No target, runtime, warehouse, entry, permission or grant was changed.
Tests/docs/manifests are local review material, not runtime upload artifacts.

All other saved runtime files are unchanged. Authentication, R1/frozen mappings,
connection/lock protection, date repair, 40053 and controlled supplements,
Spent relationships, source tracing and navigation must be preserved. Do not
copy the older root development application or a disabled-auth sharing tree.
No schema/grant scripts or historical operations are needed for these UI/draft
changes. Existing `sql/review` candidate arithmetic is unchanged apart from its superseded header;
its additive Base formula is superseded and must not certify a position.

## Release gates (future authorized operation only)

- Verify company identity, current live source drift and configuration; snapshot
  the then-current complete runtime and grants for rollback. Stop on drift.
- Confirm this exact local candidate and run the FULL offline suite (`python -m pytest -q`) and readiness.
  Keep rules PENDING and require all runtime artifacts in the upload manifest.
- Do not run SQL08/SQL18/initialization, date corrections, supplements or original
  migration for this release. A changed source manifest is not permission for
  any data fix. Restore the verified previous source if a release is incomplete
  or key pages fail; do not delete rows/history or change schema to roll back UI.
- A separate authorized R4 final-runtime verification and employee access/UAT
  plan remain to verify. No engine or company-browser acceptance is claimed.

## Staff browser smoke test — 15 steps

These are proposed steps, **not executed**. Writes need separate approval. Use
only a uniquely marked `DEV_TEST_DELIVERY_20261030_<run-id>` Account/records.
Record expected values before each step, user role, outcome and any error ID.
Do not edit real historical records, clear references or force cleanup.

1. After an authorized release, sign in as the intended staff role. Confirm
   Account, Flock, Report Center and Record Review & History load and navigate.
2. Identify/create the marked test Account and Facility with correct ownership.
   Record their IDs; confirm linked navigation returns the selected record.
3. Create marked Quota Registrations for the three canonical type choices.
   Confirm values persist and Account links remain correct after refresh.
4. On a marked registration create Purchase with positive decimal Quota Count
   and **blank Price**. Select a valid Related Account. Refresh: Price is blank,
   not 0; decimal quantity remains. Independent SQL NULL checking is to verify.
5. Create/edit a marked record with explicit Price 0. Change only Comments and
   verify 0 stays 0. On the blank-price record, a notes-only edit stays blank.
6. Select Purchase/Sale/Lease (In)/(Out) and verify required Related Account.
   A missing reference must block save. Adjustment/Base show no required star.
   Adjustment accepts finite negative/positive nonzero quantity; try a marked
   -5 decrease, then 0 (blocked). Other types remain strictly positive.
7. If an explicitly prepared marked legacy Lease In/Out fixture exists, edit
   only notes and verify old type/credit label/NULL/decimal remain. Otherwise
   mark this case to verify; do not use a real historical row to create a test.
8. Exercise Quota Registration/Transaction type filters for canonical types and
   known legacy labels. Match IDs, not names; no stored label should be rewritten.
9. Create/edit a marked Flock under the test Account/Facility and applicable
   registration. Type choices are canonical; stored legacy types stay visible
   on an existing marked fixture. Do not replay Delivery or lifecycle events.
10. On a marked Flock with reviewed Count fixtures, view Latest Count date,
    quantity and source. Same-day multi-source observations must show conflict;
    the page must not choose an arbitrary observation or change Bird Count.
11. Flock usage must say Not established. Historical registered totals are not
    current inventory. A future planned Disposal Date must not itself end/zero
    a Flock; do not change real disposal records for this check.
12. In Report Center filter quota transactions by Adjustment/Base/Lease (In),
    group by Transaction Type/Credit Type and sum Quota Count. Compare selected
    IDs and known totals with preview; never interpret that sum as entitlement.
13. Download CSV and XLSX for the same grouped result. Verify values, order,
    Credit Type label, decimals, NULL/0 distinction and filter state. Repeat for
    marked Flock Transactions and quota-type grouping; source rows must not multiply.
14. Open the same marked editable record in two sessions. Save one change; the
    stale second correction must conflict. Reload, review and explicitly
    reconfirm; do not silently refresh the expected version and resubmit.
15. Attempt deleting a marked parent still referenced by a marked child. Expect
    a blocked referenced-delete message and intact records/history. Cancel and
    log the result; arrange separately authorized cleanup without force-delete.
