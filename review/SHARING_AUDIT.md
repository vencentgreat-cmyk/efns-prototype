# Sharing audit and exclusions

Prepared 2026-10-28, offline only. No original Git history accompanies this
directory. The original branch and uncommitted work remain untouched. The
existing remote is not assumed private or safe: its history contains sample
spreadsheets, older configuration and dated documentation, and its tip predates
the candidate. This is not a full secret audit of that history; a new clean
private repository is the safer sharing boundary. `.gitignore` would not
remove old committed content, so no branch of that history is prepared.

## Exact basis

Application/configuration/deployment descriptor files are copied solely from
the verified `zero_count_revision/candidate_app` manifest, never the root app
tree. Synthetic tests and two offline helper scripts come from the associated
isolated work directory. SQL sources come from that work directory, with an
explicit exclusion list and static review notes. No saved database export or
company evidence is copied. Added review docs/harness are separately listed.

## One runtime sharing exception

`app/security.py` contained four old, salted prototype password hashes. The
sharing copy replaces exactly those four constants with an intentionally
non-login `REVIEW_DISABLED` sentinel in the same seed records. The original
hashes and a diff containing their values are **not** shared. User/domain/role
checks and hashing/verification functions are untouched. Synthetic tests create
their own random passwords, and interactive review uses a newly chosen local
password. This exception is in `CANDIDATE_CONSISTENCY.json`; all other candidate
artifacts must match their original SHA-256. **The deployment candidate itself
is unchanged. Do not deploy this scrubbed review directory.**

Company identity guards, mapping contracts, permitted email domain and object
names remain intact. `source_provenance.json` is runtime scope configuration
with batch/file IDs and scope labels; it is retained for faithful review and
is not an export of records or a fresh verification of those labels. Referenced
private evidence documents are intentionally absent. `snowflake.yml` is an
artifact/object descriptor, not a connection profile. The only TOML included is
native theme configuration; `.env.example` contains local flags only.

## Excluded material

- Real company CSV/XLSX/XLSM, screenshots, Word/PDF, transaction exports, database
  dumps/GET_DDL evidence, query results/IDs, row-level reports, original-file
  manifests, grants/role snapshots and deployment logs.
- Passwords, tokens, private keys, actual `.env`, `secrets.toml`, Snowflake
  config/connection profiles, credential-bearing URLs, auth databases and old
  prototype hash constants. No such credential files were opened for this task.
- Virtual environments, caches, logs, build/deployment output, prior archives,
  `.git` and root dirty worktree files.
- `sql/07_initial_admin.sql` (configured real administrator identity) and
  `sql/10_dev_synthetic_cleanup.sql` (cleanup not needed for source review).
- Company deployment test modules (two) depend on nonshared deployment helpers
  and evidence; `test_dev_synthetic_sql.py` exercises seed/cleanup execution
  contracts rather than the application under review and is omitted. The
  synthetic seed SQL source is retained solely for existing static checks.
- One test in manual corrections depends on the dated GET_DDL/fresh-company
  builder: it is explicitly skipped with the reason, not fabricated or passed.

## Synthetic content retained deliberately

Mapping JSON v1/v2/v3/R1, batch-scope JSON, generator code and all included
test-created in-memory CSV/XLSX are required context. No blanket CSV/JSON rule
removes them. Fixture GUIDs, placeholder names/emails and test error strings
are fabricated test inputs, not retrieved company rows or passwords.

## Test-only adaptations

- Explicit `tests`/`scripts` packages make helper imports independent of any
  unrelated installed package of the same name.
- The offline conftest creates its temporary parent directory, uses isolated
  auth storage, defaults to local/Mock, and blocks outbound socket events.
- A corrections AppTest uses a named temporary `.py` entry instead of a
  hash-named `from_string` file that Streamlit misidentifies as an empty title.
- An obsolete theme assertion now checks the actual retained light-theme and
  scoped title-contrast fix rather than forbidding all custom selectors.
- The stale-version test explicitly starts from an earlier timestamp; its
  previous wall-clock timing assumption could intermittently fail. A separate
  strict expected-failure witness preserves the equal-clock collision for
  independent review. Business implementation is not changed to hide it.

Scans are defense in depth, not a mathematical guarantee of absence. Consult
the final file manifest, static findings and source. Review any additional
files before making a first commit; keep the remote private.
