# Round 2 local validation

Baseline `9b046113eb88a598127fe21c711bc84aa6658575`; actual supplied `test_round2.py` ported with a relative ROOT. Before fixes: 23 passed / 2 failed. After fixes the supplied 25 tests pass. The B6 assertion now requires no activity to be written without re-confirmation; technical B7 checks FF9 consistency rather than documenting the old gap.

Final complete offline suite: **842 passed, 1 skipped, 0 failed, 0 xfail**. Command: `python -X utf8 -B -m pytest -q --tb=short`; local JUnit `round2/full_final.xml`. The existing skip needs a dated company snapshot not included in this offline package. This run includes actual AppTests, synthetic Mock workflows and fake Connector/Snowpark execution contracts. It is not company browser or real-engine isolation evidence.

Readiness passed with `python -X utf8 -B scripts/check_snowflake_readiness.py`. The original Git worktree is preserved. No company access, DDL/DML, deployment, historical operation, commit or push was performed. The separate sharing copy uses disabled authentication seeds; runtime and test bytes are checked against the frozen working copy.

The optional-reference Snowflake test exercises CREATE and UPDATE commit branches with a fake executor and synthetic actor; it does not prove live Snowflake behavior. Version tests simulate driver microsecond truncation unless SQL projects FF9, and reject two versions differing within the same microsecond. Timeout tests verify session SET before the owned transaction, restoration after completion, rollback and uncertain COMMIT messaging. Real DEV plan is in `DEPLOYMENT_BOUNDARY.md`.

Final source directed regression: 74 passed; sharing-copy directed regression: 55 passed. A concurrent test invocation initially had two Windows SQLite setup errors because the existing harness has a fixed temporary directory; the independent-basetemp sequential rerun passed all 74. Keep runs sequential or supply different `--basetemp` paths. After the complete run, the remaining unreachable Farm Location deletion block was removed; seven affected regressions passed.
