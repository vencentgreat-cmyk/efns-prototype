# Business Rules

> **STATUS: PROVISIONAL — These are hypotheses only.**
> None of these rules have been confirmed from the actual EIMS Dataverse system.
> They are placeholders for discussion and will be refined after Dataverse
> metadata is obtained.

## Production

### CSV Import Rules (Provisional)

1. Each CSV row represents one production observation period (typically weekly)
   for a specific grader/barn/flock combination.
2. `TOTAL_RECEIVED` should be >= `TOTAL_ACCEPTED` (Accepted = Received - Rejected - Loss).
3. Either separate `REJECTED` + `LOSS` values **OR** a legacy `LEGACY_REJECT_LOSS_TOTAL`
   should be present, but **not both** for the same row.
4. `NET_PER_BOX` should approximately equal `NET_WEIGHT / NET_BOXES`.
5. Reporting year and week are required for tracking.

### Classification (Not Yet Defined)

- Egg size bands (Jumbo, Extra Large, Large, Medium, Small, PeeWee) are
  represented via `PRODUCTION_SIZE_BREAKDOWN` (normalized child table).
- The actual size band rules/weight thresholds are **not yet confirmed**.
- Production classification categories are **not yet confirmed**.

## Quota (Phase 2 — Do Not Implement Yet)

1. Quota is registered to a specific account/producer.
2. Quota can be increased, decreased, transferred, or temporarily leased.
3. A lease has a source, a destination, a quantity, start date, and end date.
4. Lease history must be retained.
5. The effective quota for a producer at any point in time factors in active leases.

## Salmonella / Disease Testing (Phase 2 — Do Not Implement Yet)

- Testing records link to an account, facility, or flock.
- Results are positive or negative.
- **Further business rules are UNKNOWN. Do not invent them.**

## General

1. All records should have creation timestamps.
2. Updates should track modification timestamps (simplified audit trail for v0.1).
3. Deletion behavior (soft vs hard delete) has not been confirmed.
4. Required vs optional field rules have not been confirmed.
5. Duplicate detection rules have not been confirmed.