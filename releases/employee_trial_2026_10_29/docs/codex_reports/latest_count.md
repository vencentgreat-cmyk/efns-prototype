# Flock Latest Count audit — 2026-11-03

## What the screen computes

The Flock detail page passes the selected Flock and its Flock Transactions to
`flock_stock()` (`app/pages/5_Flocks.py:110-123`). The relevant stored tables are:

- `CORE.FLOCK`, selected by `FLOCK_ID`;
- `CORE.FLOCK_TRANSACTION`, joined logically by
  `FLOCK_TRANSACTION.FLOCK_ID = FLOCK.FLOCK_ID`;
- `CORE.PRODUCTION_RECORD` / `REPORTING.VW_PRODUCTION_SUMMARY`, related to the
  same Flock by `PRODUCTION_RECORD.FLOCK_ID = FLOCK.FLOCK_ID` for the separate
  **Matched Production Records** tab (`app/pages/5_Flocks.py:138-142`).

`flock_stock()` filters transactions to the selected Flock, excludes inactive
rows, ignores transactions after the Halifax `as_of` date, and keeps rows whose
stored `TRANSACTION_TYPE` is exactly `Count`
(`data/flock_stock.py:29-45`). The latest date is the maximum Count
`TRANSACTION_DATE`. Every Count row on that date is retained.

If those same-day rows contain more than one normalized `COUNT_SOURCE_LABEL`
(blank is `Unknown`) or more than one numeric `QUANTITY`, the date is a conflict
and no observation is selected (`data/flock_stock.py:46-57`). Otherwise the
first latest-day row supplies the displayed quantity. The screen labels it an
observation, not current stock.

The screen shows `Latest Count: not available.` when there is no Count row on or
before the as-of date (`app/pages/5_Flocks.py:118-121`). A same-day conflict has
a separate warning. An unusable quantity can also leave the quantity unknown;
negative or fractional Count values are rejected by the calculation, although
normal write validation is intended to prevent them.

The requested review query is
`sql/review/find_flocks_with_matched_production_20261103.sql`. It starts from
distinct non-null `PRODUCTION_RECORD.FLOCK_ID`, exactly the relationship used by
the Matched Production Records tab, and reports the latest Count date, value,
source and same-day conflict state. It is read-only and was not executed.

## Business-rule comparison

No executable behavior contradicts the four supplied rules:

- Base transactions use the latest snapshot per registration and exclude older
  Base rows (`data/quota_position.py:136-168`); the configured policy is
  `LATEST_SNAPSHOT_PER_REGISTRATION` (`config/quota_rules.json:31`).
- Adjustment accepts signed values but rejects zero
  (`data/validation.py:238-249`).
- Purchase requires a Related Account
  (`data/validation.py:218-220,266-272`).
- `quota_position` and `flock_stock` remain `PENDING`, and the UI withholds net
  quota/current occupancy unless both rule sets and evidence are confirmed
  (`config/quota_rules.json:2,20`; `app/services/quota_usage.py:77-85,128`).

Two comments are stale/uncertain rather than behavioral contradictions:
`data/validation.py:219` calls the Related Account rule “provisional”, and
`data/validation.py:239` calls signed Adjustment “provisional until staff
confirm”. Those comments conflict with the supplied status of these rules as
known, but the validators enforce the supplied behavior.
