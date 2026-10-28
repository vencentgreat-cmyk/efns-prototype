# EFNS — independent offline review

Frozen review of the **2026-10-28 zero-count business-acceptance candidate**.
This is expanded application source, synthetic tests and static SQL context,
not a dump of the original working tree or an export of company data.

## Run the tests without company access

Use Python **3.12** (the preparation machine used 3.12.14). From this directory:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# PowerShell instead:
# .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-review.txt
python -m pytest -q --tb=short
python scripts/check_snowflake_readiness.py
python scripts/check_review_package.py
```

Installing dependencies needs a package index or a prepopulated wheel cache;
running tests does not need network, Snowflake credentials or a company login.
The resolved installed dependency closure is pinned in `requirements-lock.txt`.
Fresh package download/install on Linux has not been executed here. Snowflake SDKs enable import and
adapter-contract tests only; they do not authorize any connection. The test
harness fails on network attempts and forces Mock/local runtime defaults.

See `review/LOCAL_VALIDATION.md` for actual executed commands and limitations.
One dated-company-snapshot assertion is explicitly skipped; two company
deployment test modules and a synthetic-seed/cleanup test module are excluded.
This is not a claim that those environment-dependent checks passed.

For a local interactive Mock app, keep `EFNS_RUNTIME_MODE=local` and
`REPOSITORY_MODE=mock`; run `python scripts/create_review_user.py` to create an
isolated synthetic reviewer account. Set `EFNS_AUTH_DB=.local/reviewer_auth.db`
in the same shell (PowerShell: `$env:EFNS_AUTH_DB='.local/reviewer_auth.db'`;
bash: `export EFNS_AUTH_DB=.local/reviewer_auth.db`), then run
`python -m streamlit run streamlit_app.py`.
Its password is entered locally and never packaged. Interactive startup creates
local SQLite state under `.local/`, which is not part of the review submission.
AppTests exercise the pages without requiring this manual step.

## Architecture and workflow

- `streamlit_app.py` delegates to `app/Home.py`; pages live under `app/pages/`.
  Navigation resolves the root-entry and local-entry page paths consistently.
- `app/auth.py`, `app/security.py`, `app/snowflake_security.py` implement local
  and Snowflake-viewer identity; `authorized_repository.py` applies permissions
  and audit boundaries. Synthetic test users do not represent real staff.
- `data/repositories/base.py` supplies the repository contract; `mock.py` uses
  synthetic in-memory state and `snowflake.py` uses parameter-bound executors.
  `continuity.py`, `correction_review.py`, `flock_supplement.py` and
  `flock_date_repair.py` contain history, decision and restricted repair paths.
- Production intake separates original file retention, row review, matching and
  CORE commit. Historical Migration Import retains its complete-package
  contract; Daily Flock & Quota Import accepts supported operational subsets.
- Flock, Facility, Quota and Salmonella pages use repository validation and
  authorization; reports/export use shared results, preserving NULL versus0.
- RAW is source evidence, CORE is business state, REPORTING provides views;
  revisions, decisions, audit and import tracking have distinct responsibilities.

## Latest candidate behavior and limits

**Account Bird Count aggregation is implemented. A real quota percentage is
not implemented:** no reliable real quantity/unit baseline is available.
The UI must explain why it cannot calculate capacity, remaining capacity or
percentage; synthetic arithmetic tests are not an EFNS quota certification.

Ordinary Flock Transactions record activity only. A new current Count/Removal
must use **Apply this confirmed current Count/Removal to Bird Count** plus a
reason. Count is an absolute current observation (finite integer >=0); Removal
is a positive integer deducted once and must not exceed known current birds.
Only the explicit current path changes Bird Count. Count0 is real zero, not
unknown, and does not end the Flock or change disposal dates or Status.

Same-account multi-Flock/multi-Facility totals include unassigned Facilities;
unknown Bird Count remains unknown/incomplete. Different quota types/unknown
units are not silently merged. Transaction direction, leases, current inventory
and real available quota formulas remain business limitations.

The full candidate also contains the previously deployed date batching/R1,
company identity protection, historical transaction supplement, navigation,
report count/nullable sum, original-file trace and light theme. Preservation is
checked against the frozen candidate; **this review does not connect to or
re-verify live company code**. This new business-acceptance/zero-count candidate
is not described as deployed.

## What is deliberately not here

No real CSV/XLSX, query outputs, GET_DDL evidence exports, grants snapshots,
logs, passwords, tokens, keys, connection profiles, SQLite state, virtualenv,
deployment bundles or original Git history. `sql/` contains checked source
definitions, not an assertion of current live metadata. `snowflake.yml` is the
unchanged deployment descriptor, not a login configuration and not permission
to deploy. `.streamlit/config.toml` contains light-theme settings only.

All application artifacts match the frozen candidate except four **default
prototype password-hash literals** in `app/security.py`, replaced with
non-login `REVIEW_DISABLED` sentinels for sharing. These are not working
credentials. No deployed candidate file was edited. Tests create fresh random
synthetic credentials instead of reusing company or prototype hashes.

Historical mapping JSON and `config/source_provenance.json` remain unchanged:
the latter contains a small runtime batch-scope registry with noncredential
identifiers, not row-level data. Its evidence documents are not shared and its
labels must not be treated as newly verified facts. Company identity constants,
email-domain guards and object names are retained deliberately; replacing them
would change safety behavior. See `review/SHARING_AUDIT.md`.

No license to redistribute company data or project source publicly is inferred.
Use a **private** repository and authorize the external reviewer explicitly.
