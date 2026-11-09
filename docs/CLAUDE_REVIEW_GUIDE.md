# EFNS employee-trial review guide

## Start here: choose the correct source tree

The primary current-version review target is **[releases/employee_trial_2026_10_29](../releases/employee_trial_2026_10_29/README.md)**. It contains a standalone, normal source directory: the 89 runtime files previously verified against the deployed employee-trial application, original production authentication, dependencies, synthetic tests and helpers, and structural SQL. RELEASE_SOURCE_MANIFEST.json records runtime source hashes only; it is not a business execution plan.

The root app/, data/, config/, scripts/ and sql/ directories retain the original development working tree and its previously uncommitted work. They are useful development/history context, **not a claim that every root file equals the currently deployed version**. No candidate was copied over that tree. Do not merge the older root date/transaction implementations back over the release snapshot. Historical design documents are dated references, not automatically current metadata or current defects.

This Git preparation did not deploy, query Snowflake, change authentication, rerun migrations, or rerun the full test suite. A public target must not receive this material; publication is conditional on a verified private repository and safe history. No raw company evidence is included.

## Purpose, stack and layout

EFNS supports internal egg-industry record keeping: production intake, accounts and facilities, flocks and their activities, quota registration/history, occasional Salmonella testing, reports, and traceable historical migration/correction. It uses Python, Streamlit, pandas/openpyxl, Snowflake Connector/Snowpark, and Snowflake SQL. Local Mock repositories support offline development; company deployment uses warehouse-runtime Streamlit and an active Snowflake session.

Within the current release:

| Path | Responsibility |
|---|---|
| streamlit_app.py; app/Home.py | Company root entry, application shell and registered pages |
| app/pages/ | Record workflows, imports, reports, administration and record/source history |
| app/security.py; app/auth.py; app/snowflake_security.py | Application roles, page guards, authenticated viewer and audit identity |
| app/services/authorized_repository.py | Permission checks and trusted actor propagation; frontend actor values are not trusted |
| app/services/ | Report builder/export, source-display helpers and operational workspaces |
| data/repositories/base.py; mock.py; snowflake.py | Shared repository interface, local synthetic state, parameterized Snowflake persistence |
| data/connection.py | Connector/Snowpark execution, precise versions and transaction/lock boundaries |
| data/repositories/continuity.py | Source bytes/metadata, revisions, audit, intake lock and business history |
| data/repositories/controlled_supplements.py | Restricted source-label and supplemental historical A/B operations |
| data/migration.py; config/ | Explicit historical contracts, frozen old mappings, revised future mappings and provenance policy |
| sql/ | Structural/foundation/additive/view/security scripts: executable code, not an instruction to run |
| tests/ | Synthetic Mock, fake-executor and AppTest coverage; no private business fixtures |

RAW preserves original source evidence, parsed rows, batches, validation/rejection state and target tracking. CORE holds business records. Reporting views and application report services read current CORE values. Source archives and database transactions have different boundaries: file PUT cannot be rolled back as though it were a database row. Revisions/audits and business changes that require atomicity share an owning transaction. A committed correction updates the existing business identity; old and new values must not be counted as two independent submissions.

## Business relationships and boundaries

- An Account may have multiple Contacts, Farm Locations, Facilities, Flocks and Quota Registrations. Contact rows and account-level contact attributes are distinct representations; their long-term authority/synchronization is not invented here.
- A Facility may host multiple Flocks sequentially or simultaneously. A Flock currently has one optional Facility reference; there is no fixed two-flock limit and no inferred many-to-many movement model. Existing confirmed ownership checks remain; unconfirmed cross-Account history is not silently resolved.
- Flock Transactions and Salmonella Tests refer to a Flock; Samples are children of tests. Historical test Account and Flock Account can differ under the documented exception. A source Count is an observation, not a value to add repeatedly to stock.
- Quota Transactions refer to a Quota Registration. Its Account supplies the owner relationship; a related/counterparty Account is not a substitute owner. Quota Allocations and EFC calendar records must not be given invented foreign keys merely because fields look similar.
- Production belongs to PRODUCER_ACCOUNT_ID when matched. Producer, Flock and Facility-owner Accounts remain distinct roles; housing does not transfer production ownership. Unmatched producer identities must remain source-scoped rather than merged into one anonymous producer.
- Nullable relationships do not prove that every query uses LEFT JOIN. Review actual queries and optional-link behavior. Snowflake standard-table declared PK/FK/UNIQUE metadata is not sufficient evidence of enforcement; application uniqueness, reference and concurrency checks matter.
- Estimated disposal, actual disposal and actual lifecycle events are distinct. Status/date must not automatically clear counts or manufacture an end/movement history. Unknown historical dates and associations remain unknown.

## Implemented and deployed scope — evidence levels

**Code-confirmed:** the current release contains ordinary record pages; Production and Daily Flock/Quota intake; historical migration, manual correction and restricted supplemental paths; original-file/RAW/target trace; record revisions and Flock history; role guards; separate Account relationships including Spent Fowl Plans; light UI; report filtering/group-count/export and nullable sums. Read the implementation rather than assuming a page proves every business scenario.

**Summarized prior execution records (not re-executed for this Git task):**

| Scope | Recorded outcome |
|---|---|
| Count-source label supplement | 13,556 existing transaction labels updated; independent per-GUID target/revision/audit verification completed; existing nonempty labels protected |
| Supplemental original sources | Six complete source files archived with retrieval checks; 2,043 selected source rows retained |
| Phase A | Nine original-GUID Flocks added and independently verified; no automatic extra Delivery or lifecycle event |
| Phase B | Fresh preview after A; 1,991 original-GUID transactions added and independently verified; existing transactions not overwritten; Flock quantities/status/dates not replayed |
| Held/excluded scope | 43 HOLD rows retained; 56 excluded differences not imported; original rejections and ownership conflicts not automatically released |
| Deployment | 89 remote runtime files matched the frozen candidate; owner/runtime/warehouse/entry and prior grants matched; no application rollback |
| Existing approved work | Earlier date corrections, the earlier single-Flock transaction supplement and Spent links retained; not rerun by this supplement |

The first A attempt hit the actual non-null BEFORE_DATA VARIANT constraint. Rollback was independently confirmed with zero targets/revisions/audits. The minimal fix preserves JSON null for an absent old record, without relaxing schema; an isolated real-engine check passed, then the same reviewed scope committed. The held/excluded source lists were not changed. Raw per-GUID plans, execution receipts, query history, real export files and personal information are intentionally not included in Git.

**Prior verification, with limits:** isolated real Snowflake tests exercised 501 synthetic rows/two CAS chunks, per-GUID readback, retry without duplicate writes, mandatory audit failure rollback, shared two-connection test-lock timeout/follow-up, typed dates/NULL/zero and non-null VARIANT JSON null. Local synthetic/AppTest checks covered the changed workflows. Actual company report data yielded 24 all-null Source Total groups for 1999/week 21 and 23 groups totaling 390,288 for 2017/week 15; backend results and CSV/XLSX agreed. These are prior records summarized here, not fresh database evidence supplied in the repository and not certification of all business calculations.

**User feedback:** the user reports that principal workflows have been manually tested and are usable. Treat this as user feedback, not acceptance of every role, field, import contract, browser, concurrency/failure case or historical relationship. The latest automated company-browser attempt was stopped because the tool could not reliably identify the current browser URL. Local AppTest and backend exports are not substitutes for browser acceptance. Prior records showed one active application Admin; a full employee access rollout is not implied, and no new permissions were granted by the release task.

## Inventory and quota: do not invent business truth

The displayed Bird Count summary is a **registered/historical count aggregate**, grouped by Account and compatible type, deduplicated by Flock identity. It can include ended/Depopulated/unknown-status historical Flocks and Flocks without a Facility. It is not a certified real-time inventory figure. Ordinary activity recording and the explicitly confirmed current Count/Removal operation are different paths. Count can establish zero; Removal must be positive and cannot exceed a known current count. Current-quantity changes require reviewed versions, explicit confirmation and consistent revisions/audit; historical import does not replay these changes.

Current quota percentage displays “calculation basis pending confirmation.” There is no verified current-capacity baseline or complete occupancy/exit formula. Quota Registration business numbers are not capacity quantities; Account descriptions are not authoritative balances; provincial/date Allocations are not per-Account entitlement; transaction type names and initial flags do not establish direction. Historical negative/zero values must not be discarded, absolutized, or blindly summed. Supplying one capacity number does not settle units, lease treatment, effective/expiry dates, adjustments, historical snapshots or stock inclusion.

Before a usable capacity/usage calculation, EFNS must identify authoritative opening capacity and date, compatible units/types, increase/decrease/lease/linked-transaction rules, and what counts as current occupancy (including Count observations, partial removals, lifecycle/end events, unknown dates and statuses). Code may expose evidence and limitations but cannot decide those business meanings.

## Reproduce offline without company credentials

```sh
cd releases/employee_trial_2026_10_29
python -m venv .venv
# activate .venv for your operating system
python -m pip install -r requirements-review.txt
python -m pytest tests/test_controlled_execution.py tests/test_source_field_fixes.py tests/test_account_usage_quantity.py tests/test_staff_workflow_ui.py tests/test_report_nullable_sum.py tests/test_flock_report_record_count.py -q
python scripts/check_snowflake_readiness.py
```

The release conftest forces local/Mock defaults and blocks networking. Referenced synthetic helpers and dependency pins are included. The root working tree has separate tests and potentially different intermediate code; its results must not be presented as current-release results. No full suite was rerun for this documentation/commit preparation, and no new Linux CI result is claimed.

Native-company actions in scripts/controlled_historical_supplement.py, deployment/company helper scripts, migrations/corrections, original-file archive/stage/commit commands and SQL can connect to or modify real Snowflake. Even preview/status actions can connect. **Do not run them during an offline review.** Real connection profiles, secrets and reviewed business manifests are omitted. Repository example settings are placeholders, not evidence that the company uses MFA/SSO; the recorded company connection uses its separately configured native authentication. Do not substitute the former personal trial connection.

## Where to read schema/design context

Use the release SQL, root additive scripts (including SQL19), models/repository allowlists, config mappings, business-rule documents and ERDs together. Dated field inventories, dictionaries and GET_DDL files under docs/ are historical technical snapshots; do not label their old counts or constraints as a freshly verified company schema. Operational evidence directories and raw record exports are excluded. Some old document links therefore refer to private or retired supporting evidence; their absence is intentional, not permission to fabricate it.

Operational provenance configuration is kept unchanged where it consists of non-secret classification/batch/file identifiers needed by runtime filtering; such identifiers are not proof that every EIMS_IMPORT row is genuine business data. Test/demo, unknown-source and verified business populations must remain distinguishable. No real business payloads should be used as new public test fixtures.

## Priority questions for Claude

1. What source fields, events and effective-time rules are actually available for current inventory? Locate gaps and unsafe counts without inventing a formula or replaying historical activity.
2. What authoritative quota baseline, units, transaction direction/leases and occupancy scope are still required? Propose minimal evidence requests and clearly separate structure support from business approval.
3. Find concrete employee-trial problems: edit fidelity for NULL/zero/legacy values, stale confirmation after reload, duplicate saves/receipts, concurrent changes, rollback/commit-unknown feedback, actor/permission checks, referenced deletion and report filter/export consistency.
4. Check restricted supplement/source preservation, optional links, GUID uniqueness, FF9 CAS, transaction ownership, audit atomicity and idempotence. Do not treat unforced database constraints, fake executors, green tests or page existence as sufficient proof.
5. Keep recommendations scoped to usable employee workflows. Do not expand into a new import platform, unrelated old-system investigation, new business formulas, data cleanup or a wholesale redesign.

Source-byte note: the release manifest separates captured deployed hashes from LF-normalized repository hashes. Git line-ending normalization and a whitespace-only package-initializer cleanup do not represent a functional deployment change.
