# Permit-only Flock form — 2026-11-16

Branch: `codex-flock-form-legacy-20261116`. Base: fetched main `164fd5d`, verified to contain blank-null commit `28449d2`. The existing em-dash placeholders remain unchanged.

## Before / after

| Area | Before | After |
|---|---|---|
| Default Flocks list | Flock Number and Permit Number | Flock Number hidden by column_config; Permit Number remains. The raw DataFrame still contains the original FLOCK_NUMBER, preserving data/export projections. |
| Record heading | FLOCK_NUMBER | Permit Number |
| Summary / Details | Both business identifiers | Flock Number removed from these displays; Permit Number retained |
| New form | Separate required Flock Number and Permit Number inputs | Permit Number only; FLOCK_NUMBER is set to the trimmed Permit Number on create |
| Edit form | Both identifiers editable | Flock Number absent; Permit Number read-only with “cannot be changed here” note |
| Edit payload | FLOCK_NUMBER included | FLOCK_NUMBER omitted; stored Permit Number supplied server-side regardless of disabled-widget state |
| Duplicate protection | Ordinary form had no business-number duplicate guard; batch-import guards existed | Fresh existing get_flocks read before create, trimmed/case-insensitive Permit Number comparison across all statuses (literal words such as None/NaN are not reinterpreted as missing), identifying the existing Account/Registration Number and Facility in the error |
| Hatchery / Breeder | Not entered on this form | Optional role-filtered Account-name choices, blank choice and exact stored-value preservation |

The keyword placeholder now says Permit Number, but its filter expression still searches both stored identifiers, preserving filter semantics. Status/Account/colour filters, row order, grid/selection keys, row-ID mapping and all calculations are unchanged. No other page's labels are changed: Accounts does not share this form, and its related table remains unchanged. The shared legacy column-order/label service and Report Center export definitions are unchanged.

## Confirmed decisions and limits

The user expressly authorized the page-level guard and accepted that it is **not atomic across simultaneous staff sessions**. A create can still race another session between the fresh read and commit. No repository, transaction, lock, schema, unique-constraint or SQL change is made. An atomic guarantee needs a separately authorized write-boundary design.

Permit Number cannot be changed here on edit. The duplicate guard is never run on edit, so existing legacy duplicates cannot block an unrelated correction. Existing FLOCK_NUMBER remains exactly as stored, including NF/demo/history differences. Record relationships continue using FLOCK_ID; reports, imports and other selectors may continue displaying/ordering by the original FLOCK_NUMBER as audited. No synchronization or historical data repair occurs.

The guard excludes only the target of an existing matching creation request (or the stable confirmed-initial-position request target). Existing writer replay/fingerprint verification remains authoritative. This preserves retries after a successful save whose navigation failed; it does not let a changed ordinary-create payload bypass the duplicate guard. CREATE/revision/audit writers, permission wrappers, request generation, initial-position/Delivery logic and optimistic version handling are unchanged.

## Hatchery and Breeder

Existing get_accounts results are filtered using HATCHERY_ROLE / BREEDER_ROLE, respectively. Names are stored as exact ORGANIZATION_NAME text in the existing HATCHERY / BREEDER VARCHAR fields, not Account IDs. No new SQL or Account foreign key is introduced. Duplicate identical names are offered once because the maintained target is a name string; no active-status filter or self-placeholder inference is invented.

Stored names outside the eligible lists, spelling/whitespace differences and NULLs remain selected/selectable on edit. A blank option permits explicit clearing. Both fields join the existing capture_form/preserve_form snapshot, so unchanged values are restored exactly and excluded from revision changes. A comment-only edit is tested to send only COMMENTS to revise_record, even with legacy duplicate permits and an attempted disabled Permit Number alteration.

## FLOCK_NUMBER audit and compatibility

See `FLOCK_FORM_LEGACY_AUDIT_20261116.md` for the pre-change category table and complete tracked Python/SQL/JSON/YAML inventory: **130 files, 333 matching lines**, including root legacy code, current release runtime, migrations, reports/exports and tests. It was produced before code changes and the user resolved the listed decisions before implementation. The supplied 2,220/three-differences counts are user evidence, not a live query result.

Existing tests that entered the removed widget now enter Permit Number on create or edit Comments on existing records. Date-default, confirmed placement/Delivery, occupied-Facility and normal edit assertions remain, including checks that FLOCK_NUMBER is derived only for new rows. Default-list tests now assert hidden FLOCK_NUMBER while retaining the raw data column and other labels.

## Validation

Full release suite (Python 3.12): **2,214 passed, 1 skipped, 0 failed**, 850.44 seconds. Full root suite (Python 3.11): **706 passed, 0 skipped, 0 failed**, 153.63 seconds. Focused form/date/facility/workflow/blank-null regressions: **69 passed**. Commands: `python -m pytest -q` from each directory with isolated worktree-local `--basetemp` paths. All fixtures are synthetic and all database adapters used by tests are offline. Coverage includes both app entrypoints, hidden/default versus raw identifier data, headings/Summary/Details, permit-only create, duplicate permits with case/whitespace and inactive historical rows, literal nonempty identifiers, read-only edit enforcement, legacy duplicate edits, role-account filtering/round trips/clear/preservation, unchanged revision fields, and ordinary/confirmed-position request retries. Existing blank-null, date/default/Delivery, facility-sharing and export/report tests remain in the full suites.

## Shipped-file byte proof

Expanded snowflake.yml artifacts plus streamlit_app.py, environment.yml and .streamlit/config.toml: **117 existing files before; 118 after**, because the existing service wildcard ships the new helper. Only one existing shipped file changes and one is added; **116 existing shipped files remain byte-identical**.

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| app/pages/5_Flocks.py | 38afca802dd1e2b28dda0e257a4a6756ed062aca5e01a089686427f55b8e0f08 | 13be5e21be9eca824c0754058aa02fee45adc47e687ac28f1b367e9db61c6c4f |
| app/services/flock_form_fields.py | NEW | 4b5472dbfa884e6990e871dd00efc018d35b1c49519cf5c8f23919749648e839 |

No Accounts-page, repository, schema, SQL, report, export-helper, permission, audit/revision/transaction/lock/connection-service, config or dependency changes. No real-data files, Snowflake calls, deployment or PR. The live runtime-diff manifest retains main's entries and **119 candidate hashes** are regenerated from final LF-normalized bytes, not hand-merged.
