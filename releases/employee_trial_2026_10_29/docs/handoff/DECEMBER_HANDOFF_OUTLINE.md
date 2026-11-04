# December handoff outline

Documentation skeleton, prepared 2026-11-04. All paths below are relative to
`releases/employee_trial_2026_10_29`. Unknown details are marked **TBC**.
This document records source facts and user-supplied context; it is not evidence
of deployment, database health, data freshness or staff acceptance.

Source base: `origin/codex-history-polish-r2-20261104`, commit
`d9eda0b7345de64a9583448fd5bdfda0692d1612`. December delivery owner/date: TBC.

## 1. System overview

EFNS is an internal Streamlit application in Snowflake for Accounts, Facilities,
Flocks, transactions, quota records, Production intake, Salmonella tests,
reports and source/change history.

| Schema | Purpose and examples |
|---|---|
| CORE | Business records: ACCOUNT, FACILITY, FLOCK, FLOCK_TRANSACTION, QUOTA_REGISTRATION, QUOTA_TRANSACTION, PRODUCTION_RECORD, Salmonella tables and FLOCK_EVENT. |
| RAW | Original-file metadata, import/migration batches and retained rows, producer matching evidence; examples SOURCE_FILE, IMPORT_RAW_ROW, MIGRATION_RAW_ROW. |
| APP | Application deployment and history/audit objects, including RECORD_REVISION and AUDIT_EVENT. |
| SECURITY | Application user identities/roles in APP_USER. |
| REPORTING | Reporting views, including VW_PRODUCTION_SUMMARY. |

The requested nine-module A–I designation is not established by the inspected
release documentation. Do not infer letter assignments from navigation order.

| Module | Approved name | Scope / page mapping |
|---|---|---|
| A | TBC | TBC |
| B | TBC | TBC |
| C | TBC | TBC |
| D | TBC | TBC |
| E | TBC | TBC |
| F | TBC | TBC |
| G | TBC | TBC |
| H | TBC | TBC |
| I | TBC | TBC |

Application structure:

- `streamlit_app.py`: deployment entry point; `app/Home.py`: grouped navigation.
- `app/pages/`: workflow screens, including Production Import/Data, Accounts,
  Facilities, Flocks, Flock/Quota Transactions, Quota Registrations, Salmonella,
  Report Center, EIMS Reference Data and Record Review & History.
- `app/services/`: shared workflow, reporting and display helpers; authorization
  and guarded form services are also located here and require protection.
- `data/repositories/`: repository contracts, Mock implementation and Snowflake
  persistence; `data/`: validation, intake, source tracing and calculation drafts.
- `config/`: frozen migration mappings, source provenance and PENDING quota rules.
- `tests/`: offline synthetic tests; `sql/`: structural/deployment context;
  `snowflake.yml`: deployment packaging and declared target.

## 2. Deployment and rollback — description only

Deployment is performed by the user under separate authorization. Do not execute
deployment, SQL, schema/grant changes, imports or company connections from this
outline.

1. Confirm the approved candidate commit and company identity; verify live drift,
   ownership, runtime, grants and configuration. Current live values: TBC.
2. Preserve the complete verified previous runtime/configuration and grants as
   rollback evidence. Private backup location and operator: TBC.
3. Run the offline suite and `scripts/check_snowflake_readiness.py`; review the
   artifact manifest. Use the release directory, not the older root app.
4. The package declares `EFNS_DEV.APP.EFNS_INTERNAL_APP`, entry
   `streamlit_app.py`, warehouse `EFNS_DEV_WH`, warehouse runtime. Deployment
   uses the existing `snowflake.yml`. The prior handoff specifies the company
   `efns-company` profile with an explicit `--authenticator snowflake` override;
   independently verified authentication configuration: TBC.
5. After an authorized deployment, record the actual commit, operator, time and
   browser acceptance results: TBC. UI-only history changes need no DDL or
   initialization script.
6. If rollback is necessary, restore the verified previous source package and
   configuration through the approved deployment process. Do not delete business
   rows/history or change schema to roll back a UI change. Exact backup commit,
   rollback command and post-rollback acceptance evidence: TBC.

Reference: `docs/DEPLOYMENT_CHECKLIST_20261030.md`, release gates;
`snowflake.yml`, declared target/artifacts.

## 3. Offline test suite and baseline

Use Python 3.12 and `requirements-review.txt` when preparing another environment.
From the release directory, with the existing project virtual environment:

```powershell
& '../../.venv/Scripts/python.exe' -m pytest -q
& '../../.venv/Scripts/python.exe' scripts/check_snowflake_readiness.py
git diff --check
```

The test conftest forces local/Mock defaults and blocks network. These checks do
not establish real Snowflake concurrency or manual browser acceptance.

| Source | Full-suite evidence |
|---|---|
| Original history fix `5922230` | 1202 passed, 1 skipped, 0 failed (prior handoff). |
| Inherited polish R2 `d9eda0b` | 1205 passed, 1 skipped, 0 failed; 31 warnings; 262.69 seconds (preceding task run). |
| This Markdown-only change | No runtime change; full suite not rerun. |

The pre-existing skip requires unshared installer/GET_DDL evidence. Do not count
deferred audit repros outside default `tests/` collection as passing tests.

## 4. Manual delivery-test checklist — structure only

The exact 14-step delivery-test plan is TBC. The checked-in deployment checklist
contains a different 15-step smoke test; it is not substituted here. Complete
the following rows from the approved 14-step plan before staff testing. Test
roles, approved data, issue-log location, operator and execution date: TBC.

| Step | Page | Action | Expected result | Status |
|---|---|---|---|---|
| 1 | TBC | TBC | TBC | TBC |
| 2 | TBC | TBC | TBC | TBC |
| 3 | TBC | TBC | TBC | TBC |
| 4 | TBC | TBC | TBC | TBC |
| 5 | TBC | TBC | TBC | TBC |
| 6 | TBC | TBC | TBC | TBC |
| 7 | TBC | TBC | TBC | TBC |
| 8 | TBC | TBC | TBC | TBC |
| 9 | TBC | TBC | TBC | TBC |
| 10 | TBC | TBC | TBC | TBC |
| 11 | TBC | TBC | TBC | TBC |
| 12 | TBC | TBC | TBC | TBC |
| 13 | TBC | TBC | TBC | TBC |
| 14 | TBC | TBC | TBC | TBC |

## 5. Known issues and deferred items

| Item | Verified source/context | Remaining evidence / status |
|---|---|---|
| A06/A07 admin concurrency | Prior handoff: admin updates lack reviewed-version CAS; concurrent changes can race the last-active-admin check. | Real concurrency evidence and remediation: TBC. |
| A09 report row duplication | Prior handoff: duplicate parent IDs can multiply Salmonella report rows. | Actual company duplicates and impact: TBC; do not assume duplicates exist. |
| A03 backend part | Prior handoff: Flock events compare submit-time state rather than a user-reviewed origin/version. R3 UI confirmation resets do not close the backend gap. | Backend remediation and real concurrency acceptance: TBC. |
| Large-table message size | Unbounded browse/report reads and selected RAW/VARIANT displays can create large Streamlit messages, particularly Producer matching and Original files. | Actual live volumes, reproduced limits and prioritized fixes: TBC. |
| Changed by display | Inherited polish resolves only displayed actor IDs using existing user lookups; missing/failed lookup falls back to stored ID. R2 regression test covers one failed and one successful lookup. | Deployment and staff browser acceptance of this fix: TBC. |

## 6. Out-of-scope decisions

Quota usage calculation is not in the December delivery. `quota_position` and
`flock_stock` remain PENDING (`config/quota_rules.json`). Quota registrations and
transactions remain useful as records/activity. Historical Bird Count and Count
observations do not establish current stock or occupancy. Do not enable draft
balances or usage percentages, invent unit equivalence, or make missing quota
rules block staff acceptance testing.

## 7. Suggested future work

Proposals only; owners, authorization, dates and priorities: TBC.

1. Confirm the A–I module map and recover the approved 14-step delivery plan.
2. Plan and authorize data refresh before staff acceptance (section 10), then
   reconcile the refreshed scope and retain source/change evidence.
3. Complete intended-role browser testing and a simple issue log.
4. Address backend reviewed-version/concurrency gaps under explicit write-path
   authorization; validate against real engine behavior.
5. Check parent-ID uniqueness before diagnosing report multiplication.
6. Bound large browse/report/RAW payloads while retaining source traceability.
7. Complete prioritized legacy reports, confirm printable templates and review
   the separate Flock Current implementation branch.
8. Confirm legacy quota-type semantics before expanding new-entry choices.

## 8. Legacy report parity

User-supplied inventory: legacy EIMS has **26 active reports**: **14 Flock**,
**5 Production Management**, **7 Quota**. Complete names and exact mapping of
the named reports/forms to those groups: TBC. The table records known names;
membership of each named item in the 26-report inventory must be reconciled.
The remaining report names are TBC rather than invented. Customize Report is
listed separately as a new-system capability.

| Legacy report | Group | New-system status (Available / Placeholder / Not started) | Notes |
|---|---|---|---|
| Salmonella Test Report | TBC | Available | Filterable report with CSV/XLSX. |
| Quota Summary | Quota | Available | Provisional; issuance awaits confirmed rules. |
| Flock Age | Flock | Placeholder | Business definition/as-of behavior TBC. |
| Flock Current | Flock | Placeholder | User reports implementation on `codex-flock-current-report-20261104`; completion/deployment TBC. |
| Flock Current by Producer | Flock | Placeholder | Current-state semantics TBC. |
| Salmonella Testing Form | TBC | Placeholder | Approved printable template TBC. |
| Salmonella Testing Letter | TBC | Placeholder | Template/wording/recipient rules TBC. |
| License Application Form | TBC | Placeholder | Official layout and source record TBC. |
| Flock Permit Form | TBC | Placeholder | Official permit layout/signatures TBC. |
| TBC — remaining legacy reports (expand after inventory confirmation) | TBC | Not started | Full names, group mapping and remaining count TBC. |
| Customize Report — legacy equivalent TBC | TBC | Available | New Report Center capability; not counted as a confirmed legacy report. |

Everything else is Not started per the supplied scope. Repository evidence for
available handlers/placeholders: `app/services/report_center.py`, REPORT_CATALOG.

## 9. Legacy navigation parity

| Legacy navigation | New-system treatment / staff need |
|---|---|
| Contacts | Read-only in EIMS Reference Data. |
| Allocations | Read-only; rarely used (user-supplied context). |
| Activities | Not needed by staff. |
| Provincial Marketings | Not needed by staff. |
| Quick Campaigns | Not needed by staff. |

Other navigation gaps and approved priorities: TBC.

## 10. Data currency

User-supplied context: the initial migration was reconciled on **2026-10-13**.
Flocks created in legacy EIMS afterwards, for example **40407**, are missing
until a re-migration or daily import is run. Independently checked current
database contents, subsequent refresh dates and exact missing-row scope: TBC.

Recommend an authorized re-migration before staff acceptance testing. Confirm
scope, identity matching, duplicates, reconciliation and rollback/evidence plans
before execution. This recommendation does not authorize a data operation.

## 11. Quota types

User-supplied flock-data inventory:

| Stored type | Flock count | Offered for new entry |
|---|---|---|
| Egg Production | TBC | Yes |
| Non Commercial Pullet Quota | TBC | Yes |
| Commercial Pullet Grower | TBC | Yes |
| Special Permit | 8 | No |
| Pullet Grower | 4 | No |

The legacy report parameter lists **14 quota types**; **9 have no flocks**.
The full 14-name parameter list, historical meanings and current live counts:
TBC. Preserve stored legacy labels; this outline does not authorize adding
new-entry types or rewriting historical types.
