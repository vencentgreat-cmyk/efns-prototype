# EFNS independent offline review — 2026-10-28 fixes

Expanded source and synthetic tests based on review commit `8f3733e89938cf2d6d6846e2e42583d9ff9c5730` and the saved `zero_count_revision` runtime. This is **not** a company deployment package: four prototype authentication seeds are disabled here. No original Git history, company export, credentials or live query evidence is included.

## Reproduce

Use Python 3.12; install `requirements-review.txt` in an isolated virtual environment, then run from this directory:

```bash
python -m pytest -q --tb=short
python scripts/check_snowflake_readiness.py
python scripts/check_review_package.py
```

The test harness blocks network access and uses synthetic Mock data. See `REVIEW_GUIDE.md`, `review/PROCESSING_MATRIX.md` and `review/LOCAL_VALIDATION.md`. One dated company-snapshot test is explicitly skipped; local tests do not prove live Snowflake transaction/concurrency behavior or business acceptance.

The deployment candidate separately retains its original authentication seeds. Account-level *registered Bird Count* totals are available; no certified quota denominator/percentage or validated live inventory formula exists. Confirmed Count/Removal can change stored current Bird Count; ordinary transactions record activity only.
