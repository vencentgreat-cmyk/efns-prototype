# Published employee-trial source snapshot — 2026-10-29

This standalone directory is the primary target for current-version review. Its baseline contains 89 runtime files captured from the previously verified company deployment. Local quota/flock evidence-gate changes are now present and are NOT deployed; see docs/quota_flock_review_20261029.md and QUOTA_FLOCK_PATCH_MANIFEST.json. Original authentication is preserved; this is not a disabled-seed sharing copy. The root working application is older unmerged development work and is retained without overwriting local edits.

Start with ../../docs/CLAUDE_REVIEW_GUIDE.md. The SQL files are structural context and executable deployment/migration code, not instructions to run against any account. No private source documents, company execution manifests, original CSV/XLSX/API payloads, company query results, credentials or business-row fixtures are included.

## Offline synthetic tests (no company credentials)

From this directory, in a Python 3.12 environment:

```sh
python -m pip install -r requirements-review.txt
python -m pytest tests/test_controlled_execution.py tests/test_source_field_fixes.py tests/test_account_usage_quantity.py tests/test_staff_workflow_ui.py tests/test_report_nullable_sum.py tests/test_flock_report_record_count.py -q
python scripts/check_snowflake_readiness.py
```

The conftest forces local/Mock defaults and blocks network. The full synthetic suite and referenced helpers are supplied; this preparation did not rerun that entire suite. Earlier local, isolated-engine and operational results are summarized in the review guide with explicit evidence boundaries. Linux CI is not claimed for this new snapshot.

Do not run native-company CLI actions, archive/stage/commit actions, deployment commands or SQL during offline review. Those operations require private plans/credentials and separate authorization. Public publication is blocked until the target repository is verified private; nothing in this README authorizes a push or a company write.

Source-byte note: the release manifest separates captured deployed hashes from LF-normalized repository hashes. Git line-ending normalization and a whitespace-only package-initializer cleanup do not represent a functional deployment change.
