# Per-record change history fix — 2 November 2026

Branch: `history-view-fix-20261102`, based on R3
`a7b0abb2ac7442afc300b0a2967d29678519e018`.
The user confirmed the existing `efns-prototype` origin after the initially
requested `efns-identity` URL returned Repository not found. No remote setting
was changed.

## Minimal implementation

- `data/repositories/continuity.py`: adds `get_record_revisions_for(entity_type,
  entity_id, limit=50)`. Snowflake uses bound entity/ID predicates and a validated
  integer LIMIT in SQL, ordered newest first (revision ID breaks timestamp ties).
  Mock filters before sorting/copying the limited matches. Limits must be whole
  numbers 1–200. No writer, transaction or old unfiltered getter changes.
- `data/repositories/base.py`: declares the new normal read interface.
- `app/services/revision_history.py`: pure field-difference projection, UTC
  revision time converted to America/Halifax (explicit seasonal offset), original
  recorder identity, type/reason and old/new values. NULL is an em dash, zero and
  blank remain distinct. Technical timestamps, creator/updater fields and
  underscore-prefixed metadata are ignored. No-change revisions retain one row.
- `app/pages/21_Record_History.py`: fifth Change history tab with nine supported
  business types, searchable name/ID choices and latest 50 revisions. Production
  is supported through its existing dedicated writer (not an ordinary MODEL
  key). Attribute corrections also shows only the currently selected record.
  Neither display sends BEFORE_DATA/AFTER_DATA columns to Streamlit.
- `tests/test_record_history_view.py`: 21 new synthetic tests, including filtered
  limits/order, captured parameterized SQL, old getter compatibility, existing
  normal-read authorization, NULL/0, dict/JSON snapshots, metadata exclusion,
  creation/deletion, summer/winter offsets and actual Account revision AppTest.
  The page test adds 150 large unrelated snapshots and makes the global getter
  fail if called; all displayed frames are checked for absence of raw snapshots.
- Packaging metadata/checklist and the exact package-count test change from 95
  to 96 because the existing service wildcard includes the new pure helper.
  Hash and no-deletion assertions stay in place. No other page is modified.

AuthorizedRepository already routes all get_* methods through VIEW_DATA. No
wrapper or permission changes are necessary; the tests verify allowed reads and
rejection of an inactive actor. Changed by displays the stored RECORDED_BY
identity; no unknown employee name/email is invented.

## Verification

From the release directory:

```powershell
& '../../.venv/Scripts/python.exe' -m pytest tests/test_record_history_view.py -q --tb=short --basetemp=.local/history-view-targeted-temp
& '../../.venv/Scripts/python.exe' -m pytest -q
& '../../.venv/Scripts/python.exe' scripts/check_snowflake_readiness.py
git diff --check
```

- Final targeted run: **21 passed in 5.48s**.
- Full offline suite: **1202 passed, 1 pre-existing skip, 31 warnings, 0 failed in 248.65s (4m08s)**.
- Readiness: passed. Whitespace/diff checks: passed.
- Scope check confirms no SQL, other page, authorization, writer or transaction
  changes. Removing only the new bounded method from continuity reproduces its
  exact R3 source. The unfiltered getter is unchanged.
- No Snowflake connection/deployment or company data changes occurred. SQL
  assertions use a fake executor. AppTest/Mock is not a company browser test.
- Initial targeted validation correctly exposed that the authorization wrapper
  converts AuthorizationError to RepositoryError; its regression now asserts
  the actual rejection contract without modifying permissions.
- Initial timestamp-fixture warnings were removed by constructing ISO source
  strings; no business timestamp behavior was changed.

## User-run deployment (not executed here)

Use the existing Snowflake CLI and securely configured `efns-company`
connection; no password/token belongs in the command. From this exact release:

```powershell
Set-Location 'C:\Users\Egg Farmers\Desktop\efns\efns-prototype\releases\employee_trial_2026_10_29'
snow streamlit deploy --connection efns-company --replace
```

The local snowflake.yml contains one Streamlit entity (`efns_dev`) targeting
`EFNS_DEV.APP.EFNS_INTERNAL_APP`, root `streamlit_app.py`, existing warehouse
`EFNS_DEV_WH` and warehouse runtime. This command uses that project definition.
No DDL, SQL08, SQL18, history rewrite or grant change is needed for the fix.
Deployment remains a user operation; this task did not invoke the CLI or
reconfirm its current policy/connection status. Stop if company policy blocks it.

Before replacing live, retain the current approved source/rollback version and
check drift as in the existing release process. This branch is the complete R3
candidate plus the narrow history fix, not proof that current live equals R3.

After authorized deployment, open Record Review & History, select Change
history, choose Account and an already revised Account. Check the recorded
reason, changed field and old/new values. An unchanged record should show
No recorded changes for this record yet. Attribute corrections should show
only its selected Flock/Facility history. No business test write is required
for these read-only browser checks. Actual DEV browser validation is pending.
