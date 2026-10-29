# Local validation, 2026-10-28

- Baseline: 18 reconstructed correct-behavior findings failed against the unmodified review/runtime overlay (`baseline_findings.xml`, retained outside this sharing package).
- Final isolated working copy: `python -X utf8 -B -m pytest -q --tb=short` → **789 passed, 1 skipped, 0 failed** (`full_round3.xml`, retained locally). The skip requires a dated company snapshot not included here.
- `python -X utf8 -B scripts/check_snowflake_readiness.py` → passed (static checks only).
- No company connection, real business write, deployment, Git commit or push was performed.

Warnings are pandas/test-harness deprecations, not successful live Snowflake engine results. The referenced external repro file was unavailable, so tests here reproduce its written scenarios rather than that exact file.
