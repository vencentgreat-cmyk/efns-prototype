# Historical migration: manual correction decisions

Status: local implementation and offline verification only. No company DDL,
deployment, or real correction submission was executed for this change.

## Scope and evidence

The previous implementation reconstructed rejected rows from preserved RAW,
applied already-confirmed historical exceptions, and could commit eligible rows.
It had no manual decision storage or editor; Flock ownership conflicts always
remained pending. The existing correction batch/row trace and transaction lock
are reused rather than creating a second migration system.

The user-provided correction preview contains 129 pending rows: 6 Flocks,
85 Flock Transactions, and 38 Quota Transactions. The stated split of the
transactions is 57 dependent and 28 missing a Flock. These counts describe
that supplied export, not a new live database reconciliation. None of those
rows has been confirmed or modified by this implementation.

The saved company initialization metadata and the dated DDL snapshot contain
the two correction tracking tables, but no manual decision table. Current live
metadata has not been queried in this task. Apply and verify the additive
upgrade before using the new editor; do not run initialization again.

## Four distinct operations

1. **Prepare correction preview** reads the original committed batch's rejected
   RAW, previous committed correction traces, current parents, and saved decisions.
2. **Save correction decision** requires evidence and explicit confirmation. It
   appends a versioned decision and an audit event, but does not write CORE.
   A saved decision is not necessarily valid or eligible.
3. Revalidation uses the original batch's supported mapping version and the
   existing normalizer, required/type/date/reference rules, plus the narrow
   confirmed historical exceptions. Invalid choices stay pending with reasons.
4. **Commit eligible corrections** requires a separate confirmation. It re-reads
   all persisted decisions and parents inside one transaction and rejects an
   outdated preview. Only eligible records are inserted. CORE, correction batch,
   correction row trace and mandatory audit either commit together or roll back.

Other unresolved rows remain pending. Commit corrected Flocks first, then click
**Prepare correction preview** again to assess their dependent transactions.
A dependency resolving does not waive other validation errors.

## Identity, permissions and immutability

- Original identity is `(ORIGINAL_MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)`;
  target GUIDs cannot be edited. File, row and source ID are checked against RAW.
- `RAW.MIGRATION_CORRECTION_DECISION` is append-only. It stores source identity,
  entity, request ID, version, changed fields, normalized before/after values,
  evidence, authenticated operator email, and server UTC recording time.
  Original full source values remain in immutable RAW rather than being rebuilt.
- `STATUS=SAVED` means the decision was saved, not that CORE was written. Commit
  status and time belong to the correction batch; its row records the decision
  ID/version and final target ID. The UI uses this trace for **Committed to CORE**.
- `IMPORT_DATA` is checked in the authorization proxy for save, preview and commit.
  The proxy supplies the authenticated actor; a caller-supplied actor is replaced.
  Reader roles cannot save or submit. The form has no operator identity input.
- Save uses a stable request ID and expected version. Duplicate saves are
  idempotent; conflicting or outdated versions are rejected. Committed corrections
  cannot be edited. Failed CORE submission leaves the saved decision available.
- Commit uses a reviewed-values token, receipt and the existing `RAW.INTAKE_LOCK`
  transaction row. Cooperating application correction writers serialize across
  sessions. A repeated successful submission returns its receipt, not new rows.
  An existing target without valid committed correction trace is never overwritten.
  Insert affected counts must match expected counts or the transaction rolls back.
- Snowflake standard-table PK/UK declarations are informational. These checks do
  not claim to prevent an administrator or independent non-cooperating SQL writer
  from bypassing the application. No global/future-object privileges are added.

## Allowed corrections

| Entity | Editable values | Validation and limitations |
|---|---|---|
| FLOCK | ACCOUNT_ID, FACILITY_ID | Existing Account; optional existing Facility belonging to the chosen Account. Clearing a Facility is an explicit evidenced decision, not automatic repair. Historical ownership changes that cannot be represented remain pending. No occupancy limit is introduced. |
| FLOCK_TRANSACTION | FLOCK_ID | Explicit existing Flock plus original required/type/date rules. No name/date/quantity guessing. |
| QUOTA_TRANSACTION | QUOTA_ID | Existing Quota; Owner is derived from that Quota and must resolve to an Account. Related Account/Quota/transaction references and original required fields remain validated. No editable Owner or invented number. |

The normal daily intake rules and the 14-file historical contract are unchanged.
The already-confirmed historical nullable registration-number exception remains
separate from parent-reference repair. Negative historical quota values remain
unchanged; no absolute values or zero substitution are introduced.

## Schema and installation consistency

`sql/17_Historical_Manual_Corrections.sql` is the only existing-environment upgrade:

- creates `RAW.MIGRATION_CORRECTION_DECISION` if absent (13 columns);
- adds nullable `DECISION_ID` and `DECISION_VERSION` to correction rows;
- declares a decision PK, per-source version UK and composite RAW FK;
- grants only SELECT and INSERT on the new table to `EFNS_DEV_APP_OWNER`;
- checks company organization, account, locator, region and database before DDL.

No existing business rows, RAW, batch statuses, rejection reports, or original
ID mappings are updated. No DROP/TRUNCATE/table replacement is included.
The fresh-company builder extends the saved 32-table snapshot in memory; it does
not rewrite that historical snapshot or old release package. Its current expected
structure is 33 tables plus 4 views, with 15 additional columns (594 total table
and view columns against the original 579-column company baseline). This is an
expected local structure, not a claim that the upgrade is deployed.

## Company deployment order (not executed)

Use the already configured company connection only. Do not inspect or print its
configuration or credentials. Password entry must remain hidden/local. If CLI is
still blocked by Windows policy, obtain IT approval; do not bypass that policy.

From `C:\Users\Egg Farmers\Desktop\efns\efns-prototype`:

```powershell
# First verify the target; stop unless QDCTNKN / UW19058 / CB12755 / AWS_CA_CENTRAL_1.
snow sql --connection efns-company --authenticator SNOWFLAKE --query "SELECT CURRENT_ORGANIZATION_NAME(),CURRENT_ACCOUNT_NAME(),CURRENT_ACCOUNT(),CURRENT_REGION(),CURRENT_ROLE()"
# Preserve the current app/live source and grants before replacing it.
snow sql --connection efns-company --authenticator SNOWFLAKE --query "DESCRIBE STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP; SHOW GRANTS ON STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP;"
snow sql --connection efns-company --authenticator SNOWFLAKE --filename sql/17_Historical_Manual_Corrections.sql
.\.venv\Scripts\python.exe -B scripts/check_snowflake_readiness.py
snow streamlit deploy efns_dev --connection efns-company --authenticator SNOWFLAKE --replace --prune
snow sql --connection efns-company --authenticator SNOWFLAKE --filename sql/08_post_deploy_grants.sql
.\.venv\Scripts\python.exe -B scripts/check_snowflake_readiness.py
```

Before replacement, retain/download the actual live application source through
Snowsight (the DESCRIBE output alone is not an application backup). Review the
complete package diff because the working tree contains earlier unrelated work.
The artifact globs include all three new runtime modules. Root `streamlit_app.py`,
`app/pages`, and the existing `EFNS_PAGE_PREFIX` navigation remain unchanged.
Do not use the historical frozen release manifest as the new package manifest.
If application replacement fails, restore the saved previous application source;
leave the additive table and any saved decisions intact rather than deleting them.

If CLI is unavailable, an approved operator can run the original SQL file in a
company Snowsight Worksheet as ACCOUNTADMIN. Use a newly prepared package and
manifest for web upload, not the old 66-file release or the fresh database SQL.
Do not run `--initialize`, the original 14-file import, or a bulk correction.

After applying SQL, verify its metadata output, composite key declaration,
decision columns and SELECT/INSERT grant. With secondary roles disabled, check
normal owner-hierarchy access and the existing INTAKE_LOCK row. No business
inserts are needed to verify schema permissions. Live/browser behavior is not
validated by the offline readiness script.

## Page acceptance sequence

1. Open **Historical EIMS Migration**, then **Migration history**, select the
   original COMMITTED batch, and click **Prepare correction preview**.
2. Under **Manual correction decisions**, filter **Correction entity** and
   **Decision state**, then choose **Original record** (batch-scoped RAW identity).
   Inspect original/proposed values, file/Excel row, rejection and relationship
   labels including Account names/IDs. For Quota, inspect its derived Owner.
3. Enter only business-confirmed relationship values and a specific
   **Confirmation basis / evidence**, tick the confirmation and click
   **Save correction decision**. Verify a new version, actor and timestamp;
   verify no CORE record was created merely by saving.
4. Inspect the revalidated preview and errors. Invalid decisions remain pending;
   save a new version if there is evidence for a different value. Other rows need
   not be resolved. An intervening edit or parent change invalidates the old token.
5. Only with real confirmed values, tick the separate commit confirmation and
   click **Commit eligible corrections**. Review **Committed to CORE**, current
   pending count, target GUID and trace. The prior decision is read-only.
6. After Flock commit, prepare a fresh preview for dependent transactions. Check
   their other fields before any separate submission. Do not treat the 129 real
   rows as approved test data; use synthetic tests for development acceptance.

Offline test evidence is recorded in the task report. No real manual correction,
live role test, live Snowflake transaction test, or browser acceptance is implied.

### Offline verification recorded 2026-10-21

- Full `python -m pytest -q`: 534 passed, 9 pandas/NumPy warnings.
- Manual correction test file: 26 passed, including Streamlit AppTest and the
  actual SnowflakeRepository with an isolated transactional executor double.
- Offline Snowflake readiness: passed. `git diff --check`: passed; Git reports
  existing LF/CRLF conversion notices, not whitespace errors.
- No DEV connection, schema upgrade, live SQL transaction, deployment or browser
  acceptance was executed. The supplied CSV was counted locally without copying
  real values into fixtures, logs or this document.

## Change inventory for this task

The workspace already contained earlier, uncommitted changes. This inventory
describes this task's additions, not every difference from Git HEAD.

| Files | Reason |
|---|---|
| `app/pages/17_Migration_Import.py` | Embed manual editor and token-checked review/commit without changing complete-package intake. |
| `app/services/historical_correction_workspace.py` | Entity/status filters, stable source selection, original/proposed relationship labels, evidence form and decision history. |
| `app/services/authorized_repository.py` | Require import permission and force authenticated actor; avoid an extra post-commit audit transaction. |
| `data/correction_decisions.py` | Explicit relationship-field allowlist and decision serialization. |
| `data/historical_corrections.py` | Overlay saved decisions on a copy of RAW, validate ownership, fingerprint reviewed values, verify trace versions and reject duplicate target claims. |
| `data/repositories/correction_review.py` | Shared persistent decision and atomic commit implementation for both repositories. |
| `data/repositories/base.py` | Consistent source/decision/preview/save/commit interface. |
| `data/repositories/mock.py` | Use shared workflow, isolated decision/audit storage and legacy commit guard. |
| `data/repositories/snowflake.py` | Use shared workflow, controlled table identifiers, strict insert counts for correction commits and legacy commit guard. |
| `sql/17_Historical_Manual_Corrections.sql` | Additive, guarded upgrade and exact grant/metadata checks. |
| `sql/08_post_deploy_grants.sql` | Preserve SELECT/INSERT access to the new append-only decision table. |
| `scripts/prepare_company_deployment.py` | Extend the frozen schema in memory for a consistent new installation; append-only grant. |
| `scripts/company_database_deployment.py` | Include added columns/keys in future read-only schema verification; preserve old snapshot evidence. |
| `scripts/company_application_deployment.py` | Verify actual manifest count rather than assuming every future release has 66 files. |
| `scripts/check_snowflake_readiness.py` | Check the new runtime files and additive upgrade offline. |
| `tests/test_manual_historical_corrections.py` | Synthetic workflow, authorization, UI, transaction, stale-preview, trace and retry coverage. |
| `tests/test_company_deployment.py` | Update expected current schema/package while preserving original snapshot checks. |
| `docs/eims_historical_corrections.md` | Link the extension without rewriting earlier deployment evidence. |
| `docs/historical_manual_corrections.md` | Implementation boundaries, schema, deployment order, limitations and page acceptance steps. |

This task does not edit the historical mapping, daily validation rules, root
entrypoint or navigation. No real business confirmation is inferred from tests.
