# EFNS review fixes — validation and remaining scope (2026-10-28)

## What was actually run

| Evidence | Result | Scope |
|---|---:|---|
| Baseline reconstructed D regressions | 18 failed | Expected-correct behavior against untouched review/runtime overlay; external `repros/test_review_repros.py` was not supplied. |
| Fixed isolated work: `python -X utf8 -B -m pytest -q --tb=short` | 789 passed, 1 skipped, 0 failed | Mock, AppTest, fake Connector/Snowpark SQL, full included offline suite. See `full_round3.xml`. |
| Fixed isolated work: `python -X utf8 -B scripts/check_snowflake_readiness.py` | Passed | Static deployment/schema/source readiness; no company query. |
| Independent sharing directory: package manifest and readiness | 192 hashed entries, no missing/changed/extra; readiness passed | 193 files including the manifest itself; sharing seeds disabled. |
| Independent sharing directory: complete offline suite | 789 passed, 1 skipped, 0 failed | Executed separately from the scrubbed sharing copy; `review_copy_results.xml` retained locally. |
| Original Git worktree | Unchanged Git status and branch | Work under `.local/review_fixes_20261028`; no commit/push. |

The single skip depends on a dated company snapshot excluded from the clean offline package. Pandas deprecation warnings are present. No company Snowflake write, real two-session concurrency, deployed browser UAT, SQL08/SQL18, deployment, or historical rerun was performed. Fake executors prove SQL shape and rollback orchestration, not engine isolation.

## Engineering decisions

- New and edited records have separate validation. Unchanged historical NULL, zero, decimals, inactive links and old enums survive note-only edits; changed values are validated. A persistent revision and necessary audit share the business transaction.
- Request IDs distinguish exact retry from a new operation; different content with the same ID is rejected. Navigation failure after a known save reports the saved ID.
- Existing source workbooks retain RAW identity. Production staging records a reviewed matching token; a changed account match requires explicit re-review before commit.
- Current quantity uses reviewed version **and** Bird Count; explicit reload keeps the draft reason but clears the application checkbox. A new confirmation is required. Halifax business day is calculated from a timezone-aware instant.
- Ordinary writers and deletion participate in the existing `RAW.INTAKE_LOCK` protocol. This serializes cooperating application paths but does not prevent arbitrary outside SQL from bypassing application-only rules.
- Unsupported report filters are rejected; the UI disables irrelevant filters and clears stale dataset state.
- Account-level display is a *registered Bird Count* summary over all statuses. It is not a certified occupancy or quota percentage. No quota denominator was fabricated.

## Still requiring evidence or decision

1. Real company Snowflake two-session tests for lock/CAS, exact affected-row behavior, mandatory audit/revision rollback and normalized timestamp precision. This task had no company write authorization.
2. Company browser UAT for all changed forms, stale review reload, CSV/XLSX and role denials after any future deployment.
3. EFNS decision on quota units, transaction direction and effective dates; ended-Flock inclusion, appropriate Bird Count correction rights, and Salmonella/sample semantics. The six cross-Account historical Flocks and their dependent transactions remain pending.
4. The raw saved-live snapshot directory currently denies read access; the readable `zero_count_revision/rollback_app` was created from it earlier and its 76-file hash manifest was verified in this run. Before a future deployment, re-query live sources and stop if drifted.

This is **suitable for independent code review and synthetic UAT**, not a declaration that live business data or production operations are accepted.
