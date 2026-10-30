# EIMS historical correction preview

This workflow applies confirmed business exceptions to rejected rows from a
committed EIMS migration without changing the original batch, RAW payloads,
validation errors, or lineage.

Jensen has confirmed that the fourteen CSV files are the full EIMS export,
not a sample. Missing relationships must therefore be investigated in that
export rather than explained by an assumed missing sample file.

## Current review and followup corrections

The read-only DEV audit on 8 October 2026 confirmed the original batch is
`COMMITTED`, and the first correction round is `COMMITTED_WITH_PENDING`.
All 112 corrected targets exist, match their stored corrected fields, and
do not overlap the original migration ID mapping. The unresolved count is
159: six Flock/Facility Account conflicts, 28 null Flock links, 57 transactions
blocked by those conflicted Flocks, 38 null Quota links, and 30 transactions
blocked by unresolved parent transactions. No conversion error was found in
these pending rows.

The correction preview now distinguishes `ALREADY_COMMITTED`, `READY_CORE`,
and `PENDING_CONFIRMATION`. A committed correction counts as resolved only
when its source identifiers match the preserved RAW row and the target exists.
An unexplained existing target or a missing committed target remains a review
issue. The stored batch count is labelled as the count at that commit; the
current preview provides the current count.

When additional rows become eligible, a deterministic followup batch ID is
derived from the eligible RAW row IDs and corrected values. Its tracking rows
have separate IDs and preserve the original RAW-row references. Earlier
committed correction batches and tracking rows are not rewritten. Repeating
the same committed round returns no new writes. CORE and new correction
tracking are saved in one transaction; failed writes roll back together.
The confirmation control is specific to that correction round.

No additional DEV records were imported during this review. Exact source
permit matches and related-transaction GUIDs found for the 28 null Flock links
are candidates for EFNS confirmation, not authority to infer a Flock owner.
Negative historical values remain unchanged. These changes require no DDL.

## Confirmed handling

- Historical quota registrations may have a null `REGISTRATION_NUMBER`.
  Daily quota creation and operational imports still require the number.
- Historical Salmonella Test Account may differ from the referenced Flock
  Account. Both references must exist and are preserved.
- Flock/Facility Account conflicts remain pending and unchanged.
- Flock and Quota transactions with missing or unresolved parents remain in
  the correction tracking area with `RELATION_STATUS = 'UNVERIFIED'`. They are
  not written to CORE and therefore do not participate in balances or flock
  inventory calculations.
- Corrected CORE writes retain the original Dataverse GUID and are idempotent.

## Reconciled preview

For `DEV_MIGRATION_255ef9b50a52e766a7dff9`:

| Entity | Eligible for CORE | Pending confirmation |
| --- | ---: | ---: |
| QUOTA_REGISTRATION | 13 | 0 |
| SALMONELLA_TEST | 7 | 0 |
| QUOTA_TRANSACTION | 92 | 68 |
| FLOCK | 0 | 6 |
| FLOCK_TRANSACTION | 0 | 85 |
| **Total** | **112** | **159** |

The 159 pending rows comprise 72 direct issues and 87 dependent rows. The
dependent rows are 57 Flock Transactions and 30 Quota Transactions whose
referenced parent remains pending.

## Facility/Flock audit

The source contains 95 Facility GUIDs referenced by 657 distinct Flock GUIDs.
Of these links, 651 use the same Account and are already in CORE; six have a
Flock/Facility Account conflict and remain rejected. Case-insensitive GUID
comparison found zero RAW-to-normalized Facility ID changes, so these shared
Facility relationships originated in the source rather than mapping logic.
Each affected Facility is referenced by 2 to 19 Flocks.

Sara confirmed on 8 October 2026 that sequential and concurrent Facility use
by multiple Flocks is valid, with no fixed maximum. The previous permanent
one-Flock interpretation is superseded; no uniqueness or overlap constraint is
appropriate. This does not resolve the six cross-Account Flocks or their 57
dependent transactions. The current pending total remains 159. No original RAW,
committed target or correction row is changed by this clarification.

## DEV preparation

Run `sql/13_EIMS_Historical_Corrections.sql` in Snowsight before deploying the
application changes. The script is additive and repeatable. It:

1. makes only `CORE.QUOTA_REGISTRATION.REGISTRATION_NUMBER` nullable;
2. creates `RAW.MIGRATION_CORRECTION_BATCH`;
3. creates `RAW.MIGRATION_CORRECTION_ROW`;
4. grants the application owner access to those two tracking tables; and
5. returns `READY_FOR_HISTORICAL_CORRECTION_PREVIEW` when verification passes.

Running the SQL does not import the 112 rows. The Historical EIMS Migration
page provides a separate preview and explicit commit action after deployment.
# Manual decisions (local extension, 2026-10-21)

See [historical_manual_corrections.md](historical_manual_corrections.md) for the
versioned manual decision editor, additive SQL 17, token-checked commit, tests
and company deployment sequence. Saved decisions and eligible previews are not
CORE commits. The original migration and rejection evidence are unchanged.
