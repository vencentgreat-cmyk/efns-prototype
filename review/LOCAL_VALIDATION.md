# Actual local validation — 2026-10-28

Executed from this expanded review source, using the existing project Python
3.12.14 environment on Windows. No company connection/configuration or SQL
execution was used. The copied test helpers are local to this source tree.
The original worktree's Python environment supplies packages only, not runtime
source. No fresh internet dependency install was performed; exact installed
dependency closure is recorded in requirements-lock.txt (66 packages).
Linux/cloud installation and the prepared CI workflow remain unexecuted.

## Commands actually executed

```text
python -B -m pytest -q --tb=short --junitxml=.local/offline-review.xml
python -B -m pytest tests/test_current_count_zero.py tests/test_review_boundaries.py -q --tb=short --junitxml=.local/final-targeted.xml
python -B scripts/check_snowflake_readiness.py
python -B scripts/static_schema_index.py
python -B -m pip check
```

`python` above denotes the original project's `.venv/Scripts/python.exe`, with
working directory set to the review source. Raw outputs/JUnit, absolute personal
paths, hostnames, databases and temporary test artifacts are NOT in the shared
tree. Counts below are derived from those actual JUnit outcomes.

- Full included suite: **747 passed, 1 skipped,
  1 expected failure**, 99.25s. No unexpected failure/error.
- After the final harness safety/timezone/disabled-seed check additions:
  **18 passed, 1 expected failure**,
  4.83s. These sets overlap; do not add them together.
- Readiness: passed, offline static checks only.
- Static SQL index:317 source declarations; NOT a live table count.
- pip check: no broken requirements in the tested environment.

## Failed preparation runs were not hidden

The first assembly run had missing temporary-parent setup, an obsolete theme
assertion and a Streamlit hash-named AppTest entry issue. These were review
harness/test-context issues; fixed only in this review copy. A later full run
exposed equal-clock version reuse in Mock; see KNOWN_REVIEW_FINDINGS. That case
remains as a strict expected failure, not a runtime fix. The stale-version
test now deliberately uses a different prior token rather than timing luck.

The final full run preceded one additional disabled-seed safety test and
the final dotenv/timezone flags; the final targeted rerun includes them.
Run the documented full command in the destination environment for its final
result. No claim is made that a new GitHub/Linux runner has passed.

## Not locally certified

Actual company schema, grants, account identity, stage/file retrieval, network,
multi-session Snowflake concurrency, engine SQL/transactions and browser staff
acceptance require separately authorized infrastructure. One snapshot-based
schema assertion is skipped. No SDK fake or Mock thread test is called real
Snowflake validation. A known Mock timestamp-collision witness is expected to
fail; investigate independently rather than treating the green process exit
as complete correctness.
