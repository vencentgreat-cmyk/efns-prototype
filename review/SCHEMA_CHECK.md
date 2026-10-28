# Static SQL scope — not a live schema export or deployment plan

SQL files are original local source definitions selected from the isolated
candidate work directory, **not** fresh company metadata. No database was
connected to, initialized or queried in preparing this review. The generated
`SQL_OBJECT_INDEX.csv` lists declarations and their source locations; repeated
names across bootstrap/upgrade scripts are versions, not additional tables.
It is not an effective-schema inventory, so do not derive a live table count.

## Checked review areas

- CORE Account/Contact/Farm Location/Facility/Detail, Flock and transactions,
  Quota registration/transactions/allocation, tests/samples, calendar; production
  records and size children; RAW import/migration/correction/source identity;
  match decisions, revisions, events, audit/security and reporting views.
- Migration RAW/correction references use the original batch plus RAW row ID;
  inspect SQL14 and the repository paths rather than assuming a raw ID is
  globally unique. Date lineage has source identity separate from target DAY.
- Source identity/history SQL16, manual decisions SQL17, nullable count-source
  SQL18 and view definitions are present. Read exact PK/FK, nullable and data
  types in these sources. Standard-table declared keys do not alone prove
  enforcement, data validity or distributed idempotence.
- Static Snowflake readiness checks execute offline against these sources.
  Passing them does not prove Snowflake syntax, actual grants or current schema.

## Discrepancies retained, not silently rewritten

1. `02_core_tables.sql` still declares positive-only Flock transaction
   `QUANTITY > 0`, while `10_EIMS_V3_DEV_Deployment.sql` defines/conditionally
   changes it to `QUANTITY >= 0`. The latter permits confirmed Count0 at storage
   level; normal positive-only rules are in the application. SQL02 also retains
   an older nonnegative Birds Disposed CHECK. Historical signed values and
   previously applied DEV changes must not be inferred from SQL02 alone.
2. SQL16 includes an old personal-account guard. It is retained **as source
   review context**, not a usable company install command. This package excludes
   the company initializer and actual snapshot. Do not run it, replace its
   safety guard or infer the company uses that old account.
3. Bootstrap and incremental scripts overlap and some upgrade scripts contain
   guarded metadata DML. No concatenation into a new install script has been
   attempted. No database upgrade is authorized by this source-review package.
4. The configured administrator bootstrap and cleanup script are omitted to
   avoid sharing real administrator identity/unnecessary cleanup operations.
   Existing static checks do not prove initial-admin or deployer permissions.

These are review findings about *source/deployment reproducibility*, not proof
of a current company schema defect. A reviewer can audit repository columns,
mapping fields and SQL dependencies locally. An actual deployment should use
the separately controlled company release process and current metadata, not
this review-only directory.
