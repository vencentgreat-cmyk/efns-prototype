# Findings left visible for independent assessment

## Confirmed synthetic boundary: repeated Mock version timestamp

The first complete-source offline run exposed an intermittent failure in the
quantity stale-version test: two closely spaced writes can receive the same
wall-clock `UPDATED_AT` in Mock. A request holding that unchanged timestamp
does not appear stale. The fixture now sets a distinct earlier timestamp to
test ordinary stale rejection deterministically; **that is not a runtime fix**.

`tests/test_review_boundaries.py` freezes the Mock wall clock and preserves the
failure as strict `xfail`. Expected behavior is to reject the stale distinct
request; current Mock behavior accepts it. If this unexpectedly passes, pytest
fails the strict marker so the status cannot silently disappear.

The application runtime is unchanged. No company Snowflake CAS test or real
write was performed, and a wall-clock witness in Mock does **not** establish
the frequency or presence of this defect in Snowflake. The reviewer should
examine token advancement and atomic SQL predicates independently. Do not claim
unconditional concurrency acceptance based on the earlier passing tests.

## Deployment-source drift, not a diagnosed live defect

See `SCHEMA_CHECK.md`: SQL02 versus SQL10 quantity constraints, legacy SQL16
account guard and overlap of old bootstrap/incremental scripts remain visible.
The runtime candidate is faithful to the frozen package; this is not a fresh
deployment bundle. No SQL has been executed or corrected in this task.

## Unverified external behavior

- Fresh dependency installation on Linux/GitHub runners, CI execution and
  browser interactions are not established by the Windows offline run.
- SQL execution, grants, actual schema/data, multiple live Snowflake sessions,
  company identity resolution and stage/file retrieval require company access;
  they were not attempted. SDK fakes are local contract evidence only.
- Real quota capacity, compatible quantity units and direction/effective-date
  formulas remain business inputs. Account Bird Count aggregation alone does
  not supply a quota denominator.

The reviewer should report further defects rather than treat this list as
exhaustive. No expected-failure assertion is a business certification.
