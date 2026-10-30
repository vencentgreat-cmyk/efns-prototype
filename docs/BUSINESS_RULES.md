# Business Rules

> **STATUS: MIXED — Confirmation status is stated per section.**
> The Facility/Flock section below is confirmed by Sara on 8 October 2026.
> Other provisional sections retain their own confirmation status.
> Unconfirmed rules remain discussion placeholders; the dated confirmation
> below must not be treated as provisional.

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

## Quota (Implemented records; balance definition remains provisional)

1. Quota is registered to a specific account/producer.
2. Quota can be increased, decreased, transferred, or temporarily leased.
3. A lease has a source, a destination, a quantity, start date, and end date.
4. Lease history must be retained.
5. The effective quota for a producer at any point in time factors in active leases.

## Salmonella / Disease Testing (Implemented records; statistical definitions provisional)

- Testing records link to an account, facility, or flock.
- Results are positive or negative.
- **Further business rules are UNKNOWN. Do not invent them.**

## Deployed technical rules (12 October 2026)

- Historical RAW identity is `(MIGRATION_BATCH_ID, MIGRATION_RAW_ROW_ID)`.
  Correction source references include the original batch. ID map uniqueness is
  one lineage per full RAW source identity, not one per date source/target DAY.
- Preserve all additional date lineages. Existing duplicate-date map UUIDs were
  paired canonically with equivalent source rows; the old UUID-to-row order was
  not stored and is not claimed as recovered evidence.
- Account self-link `None`, `null` and blank placeholders become SQL NULL.
  Real non-null references must exist and cannot point to the same Account.
- Unknown production measurement SUM remains NULL, including no-record and
  all-null sets. Counts return zero for no records. True zero, mixed known/null,
  signed measurements and cancellation to zero remain distinct from unknown.
- Future repository business timestamps are UTC NTZ; aware audit/security times
  retain offsets. Historical NTZ without provenance is not labelled UTC/Halifax.
- Current correction preview separates already committed targets, newly eligible
  targets and pending relationships. Missing committed targets are integrity
  issues, not a reason to silently repeat the insert.
- Standard-table PK/FK/UNIQUE declarations are informational; enforced NOT NULL
  and CHECK constraints remain separate from repository validation. Session
  locks do not guarantee uniqueness across independent sessions. The integrity
  export script is on-demand, not scheduled monitoring.
- A DEV migration prefix is not evidence of synthetic data. Automatic batch
  cleanup is disabled until explicit provenance and shared-reference review;
  original sources, errors, date lineage and correction traces cannot be cleared
  through the old prefix-only procedure or UI.
- The obsolete permanent one-Flock-per-Facility rule (historical R26) is retired.
  Concurrent/sequential Flocks are allowed; no numerical occupancy limit is added.

The metadata-backed workbook and `effective_rule_implementations.csv` accompany
the current review. Function counts are not asserted to be a business-rule count.
Daily requiredness and historical exceptions must be read separately.

## General

1. All records should have creation timestamps.
2. Updates should track modification timestamps (simplified audit trail for v0.1).
3. Deletion behavior (soft vs hard delete) has not been confirmed.
4. Required vs optional field rules have not been confirmed.
5. Duplicate detection rules have not been confirmed.

## Facility and Flock (Confirmed 8 October 2026)

- One Facility may have zero or many Flocks, successively or concurrently.
  Two simultaneous Flocks are explicitly permitted; no maximum was confirmed.
- A Flock has one optional Facility reference in the deployed historical model;
  daily entry requires a Facility. Multiple Facilities per Flock are not confirmed.
- Preserve each Flock GUID, its original references and history. Do not enforce
  uniqueness on `FLOCK.FACILITY_ID`, single-active occupancy, or non-overlap.
- `PLACEMENT_DATE` and `DISPOSAL_DATE` record available start/disposal dates;
  unknown dates remain null. `EST_DISPOSAL` is a forecast, not an actual end.
  Disposal alone is not proof of a complete facility-occupancy interval or current
  inventory; partial disposal and exact current-state rules still need confirmation.
- Flock/Facility Account equality remains an application and historical migration
  validation, not an implication of the two separate Account foreign keys.
  Shared facilities do not authorize cross-Account use or ownership changes.
- Report at the Flock, transaction or production row grain before aggregation.
  Join production by `FLOCK_ID`, not every Flock at the same `FACILITY_ID`.
  Sum historical Bird Count is not a verified current occupancy calculation.

See [Facility/Flock design review](FACILITY_FLOCK_DESIGN.md) for deployed evidence,
the ERD and pending migration impact.
