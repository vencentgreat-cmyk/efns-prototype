# Local validation, 2026-10-28

- Round-2 baseline: the supplied test file reproduced 23 passing / 2 failing tests (`round2/baseline.xml`, retained locally).
- Final isolated working copy: `python -X utf8 -B -m pytest -q --tb=short` → **842 passed, 1 skipped, 0 failed** (`round2/full_final.xml`, retained locally). The skip requires a dated company snapshot not included here.
- `python -X utf8 -B scripts/check_snowflake_readiness.py` → passed (static checks only).
- No company connection, real business write, deployment, Git commit or push was performed.

Warnings are pandas/test-harness deprecations, not successful live Snowflake engine results. The round-2 external repro file was supplied and ported directly; only its absolute ROOT and the obsolete failure-witness assertions were changed.
