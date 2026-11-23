# Lessee lease related records — 2026-11-23

Branch: `codex-lessee-related-records-20261123`; base origin/main `9ade5bad6b8c41d67b6a3d41b34dec5ae4b50306`.

## Cause and display changes

`app/pages/7_Quota_Registrations.py` previously loaded stored transactions only by QUOTA_ID. A new-method lease has just one stored Lease (Out) row on the lessor registration; it cannot appear in the lessee's stored table. Legacy two-row leases already appear through their own QUOTA_ID and remain unchanged.

The existing stored Quota Transactions table, count and navigation are unchanged. Below it a separate **Leased in (from lease records) (N)** section shows Transaction Type (Lease (In)), Start Date, Effective End Date, Current Quantity, Lessor Account, Status and Note. Select a row and choose **Open original lease record** to view the existing stored transaction. This is a read-only projection, never a new business record or report input.

For lessors, **Lease record status** adds effective values/status beside the unchanged stored table. The original Quota Transaction Summary also has a **Current lease status** block, because its existing primary date/count fields show the original stored values. Existing adjustment/void actions and their permissions remain unchanged.

## Resolution and edge cases

- Match RELATED_ACCOUNT_ID to the viewed registration's ACCOUNT_ID, and the source registration's Quota Type to the viewed Quota Type, using existing quota-type aliases. Only TRANSACTION_METHOD=Lease participates; legacy Lease (In)/(Out) rows with a null/allocation method are not duplicated.
- Existing `get_quota_transactions(account_id=...)` reads owner OR related account and attaches adjustment evidence through `data/quota_lease_adjustments.py`. No repository, query, SQL, DDL, connection or persistence changes were needed. Adjustment history remains one bounded read for the returned leases, not one query per row.
- Reuse `data/quota_leases.py::lease_adjustments`, `effective_lease_end` and `effective_lease_amount`. No amount/end-date rule is reimplemented. The display date is today in America/Halifax and appears in the caption.
- Current Quantity is the unsigned effective lease amount on that date: active amount after effective partial returns, zero for scheduled/ended/voided leases. Original amounts/dates remain available on the original record. Inclusive end dates and full returns follow the existing resolver.
- Status: Active, Scheduled or Ended, with adjusted/early-ended annotations where applicable; Voided explicitly says it no longer affects quota. Unusable evidence shows Needs review and unknown values, never an assumed unadjusted quantity. A verified void remains Voided/zero even if its date evidence needs review.
- No lessee registration: no page/derived registration is fabricated; a missing requested registration uses the existing Not Found state. The original lease is still visible on Quota Transactions. Missing account/type cannot match; a missing source registration cannot establish a Quota Type and is not guessed.
- If several registrations share the lessee account/type, each can show this same read-only account-level relationship. Nothing is assigned to a new QUOTA_ID, counted in stored rows or supplied to calculations/exports. No new Active-registration restriction is introduced for viewing historic relationships.
- Reporting Viewer retains VIEW_DATA access and can open originals; derived tables never have edit controls. Original editing, voiding and adjustment permissions are unchanged.

## Consistency review

Quota Transaction Details needed the effective-status block described above. The Quota Transactions list and Accounts related section list stored originals with both parties; they retain that stored-record purpose/count. An analogous directional section on the Accounts page, and clearer directional wording in the stored transaction list, could be follow-ups; they are not calculation defects and were left unchanged. Existing lease reports already use `projected_lease_rows` with adjustment evidence, and Flock Status/Flock Summary use the confirmed position resolver: no treatment change is needed. Reports, totals, export inputs and calculations are untouched.

## Validation

Synthetic fixtures only, no real names/data or workbook files added. Coverage includes active/voided/early-ended/partial/full-return leases; future and historical daily effects; legacy rows; type mismatch/missing registrations; invalid evidence; bounded offline Snowflake reads; unchanged stored rows and quota report output; Admin/Reporting Viewer navigation and read-only state through both app entrypoints.

Full release suite (Python 3.12): 2,478 passed, 1 skipped, 0 failed, 0 errors. Full root suite (Python 3.11): 706 passed, 0 skipped, 0 failed, 0 errors. Focused lease suite: 84 passed. Existing report fixture expectations were not changed. Regenerated manifest: 168 candidate hashes. Only pages 7/8 and the new display helper are changed runtime files; data/repositories, lease rules, quota/report calculations and stored records are unchanged. Manifest regenerated from main with LF-normalized candidate hashes; no hand merge.

## Shipped-file comparison

Compared against base Git-tree bytes (LF-normalized text; binary assets unchanged): 132 current artifacts, including the new helper; 129 unchanged. Only these runtime files differ:

| Path | Before SHA-256 | After SHA-256 |
| --- | --- | --- |
| `app/pages/7_Quota_Registrations.py` | `bb1bcaffa0f851ce1f38b808ec540a0a6b686dfb13413e24fee1202dad2ce3f0` | `7956534faf4674445a36016c07867805f54d34d8d25adb1686c542f961a73dbd` |
| `app/pages/8_Quota_Transactions.py` | `25e9ea1ff7011fa7d4b372f2545e45020375b4928b7d0fd1351f5b29ef8c0f42` | `de513832417025d5ea45e649fbe4eb5fd7c5772bef33de72344232a35fc9b172` |
| `app/services/quota_lease_display.py` | `new file` | `52d62f3b4aadeae514316a62966061164880331ce0659678fe450b23ae36fbaa` |
