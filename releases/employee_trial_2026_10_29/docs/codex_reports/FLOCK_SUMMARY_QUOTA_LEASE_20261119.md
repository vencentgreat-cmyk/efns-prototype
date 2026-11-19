# Flock Summary and quota lease work - 19 November 2026

Base: fetched origin/main `6b5b8883d663552bdb651bd3e560541f94c1e808`, containing Task 1 `fd1637506533095134c88d5fd8fdc545f591dd6b`. Branch: `codex-flock-summary-lease-20261119`.

## Current quota calculation and persistence map

| Area | Current path | Meaning before Part E |
|---|---|---|
| Confirmed quota | `data/confirmed_quota_position.py:16` | Active owner registrations and transactions; RAW migrated inactive-state exclusion; latest Active Base by effective/creation date, or all eligible transactions if no Base; signed amounts, effective-date cutoff and lease expiry. Missing state evidence remains unknown. |
| Quota Summary / Details | `app/services/report_center.py:165`, `:218`, `:234` | Repository accounts/registrations/transactions plus bounded state evidence feed confirmed position. Summary is net; Details preserves gross increasing-type sums and repeated account totals. |
| Flock Age / Status utilization | `app/services/flock_age_report.py:22`; `app/pages/4_Reports.py:76` | Confirmed Egg Production owner positions supply account Quota, allocation and Inventory/Quota utilization. Shared inventory computation is separate. |
| Producers Over Quota | `app/services/producers_over_quota_report.py:20` | Same confirmed quota basis, existing Flock Status summary, producer inventory/confirmed quota, and the Task 1 overall total. |
| Quota transaction/lease/history reports | `app/services/quota_reports.py:59` | Active owner/registration scope; stored legacy Lease (In)/(Out) types, dates and signed confirmed-position evidence. History retains its existing running-balance/snapshot distinction. |
| Historical quota usage panel | `app/services/quota_usage.py:19`; `data/quota_position.py:89` | Separate evidence-gated draft. UI remains hidden; current occupancy/units and flock_stock remain PENDING. It is not the established report utilization calculation. |
| Entry, atomic save and history | `app/pages/8_Quota_Transactions.py`; `app/services/form_safety.py:71`; `data/record_safety.py`; `data/repositories/continuity.py:285` | Existing quota rows are stored in CORE.QUOTA_TRANSACTION, linked to the owner's registration, with related counterparty/date/count fields. Forms use idempotent creation or revision, existing serialization, permission checks and audit/revision conventions. |

## Part D: stopped at the explicitly required calendar gate

No Flock Summary report was made Available, and catalog counts were not changed. The existing production-week functions at `app/services/production_reports.py:62-95` validate YYYYWW, enforce start <= end, and obtain reporting year/week codes; they do not return week start/end dates. `app/services/report_center.py:317` explicitly rejects inferring calendar date ranges for Production reports.

CORE.DIM_EFC_DATE (`sql/02_core_tables.sql:301`) and its existing read method (`data/repositories/snowflake.py:1846`) contain DAY, EFC_YEAR, EFC_WEEK_NUMBER and other labels. The v3 migration maps these source attributes (`config/eims_migration_mapping_v3.json:258`). However, no existing tested resolver establishes production SOURCE_WEEK_CODE -> EFC day membership -> complete week start/end boundaries. The dimension's presence alone does not authorize choosing ISO weeks, a weekday anchor, or min/max dates from potentially partial mappings.

The requested instruction was to stop Part D if existing production-week logic does not provide start/end dates. Accordingly this commit records the gap instead of inventing a calendar or shipping a misleading runnable report. Completion needs a confirmed relation between production week codes and a verified complete date dimension (including year boundaries), plus synthetic week-boundary tests. No stock is summed across weeks and no zero-filled inventory is invented.

## Part E: allocation and effective-dated leases

The user explicitly authorized narrow quota validation/persistence edits. The existing continuity transaction and global intake-lock row are reused unchanged. All new Snowflake availability reads and the new-lease write use the owning transaction executor. Synthetic two-session tests exercise the existing lock boundary; concurrent leases cannot both spend the same capacity. Employee allocation creation/revision and staged operational intake already use that boundary. No authentication, connection, lock implementation or unrelated write path changed.

A nullable `TRANSACTION_METHOD` column distinguishes new Lease entries. Missing/NULL/Allocation methods retain every existing allocation rule, including historical transaction types named Lease (In)/(Out). No backfill is performed. The Allocation form retains its payload and save behavior. The Lease form selects lessor, lessee, matching quota type/lessor registration, positive whole-bird amount, Start Date and Quota End Date. Both Accounts must exist and have an Active registration of that type.

One saved Lease (Out) row records both parties. Read-only projections show Leased out and Leased in; no second persisted row can become detached. Confirmed positions overlay the same signed quantity after allocation snapshot selection, so a later Base does not absorb a still-active new lease. During the inclusive period, lessor quota falls and lessee quota rises equally. The next day the overlay disappears automatically, without a scheduled job or record update. Unknown state evidence remains unknown.

Availability is checked at both endpoints and every effective-date or expiry-following-day boundary inside the entire requested period. This includes existing incoming leases expiring during the new period and future Base/transaction changes already recorded. Invalid/insufficient/unknown evidence rejects the save. Employee create idempotency, mandatory revision/audit and rollback remain in their existing transaction. Saved new leases are read-only: edit/delete are rejected server-side pending correction/early-return rules.

### What changes once leases exist

- Quota Summary net Issuance and producer count use the adjusted as-of position. Quota Summary Details remains gross: incoming leases add to Lease (In), while outgoing leases are not subtracted from its increasing-type totals. Its gross grand total is not a conserved net entitlement.
- Flock Age, Flock Status, by-Producer variants, Producers Over Quota and other existing users of `build_flock_age_quotas` receive adjusted account Quota/Utilization and their existing provincial metrics. Inventory calculations are untouched. Province net quota stays conserved when both parties are in the report's scope; a filtered subset need not conserve its own total.
- Quota History and transaction reports show both read-only directions with plain labels. As-of projections show new leases only inside their active period; date-range transaction reports retain them when any requested day overlaps. The operational list and Record History retain the saved record after expiry.
- The hidden historical usage panel's evidence-gated draft also overlays new leases, including incoming leases. It remains hidden; stock/units gates remain unchanged/PENDING and no unverified usage figure is enabled.
- License quota and any other established caller of confirmed quota position inherit the same adjusted as-of quota. Existing allocation-based amounts, legacy rows, and all numbers when no new lease exists remain unchanged. Before/after-period as-of projections match the original allocation-only result.

### Conservative assumptions / limits for staff confirmation

1. Quota End Date is inclusive (`LEASE_END_DATE_INCLUSIVE=True`); return occurs the next day. No time-of-day proration.
2. Overlaps are permitted only if the sum of existing commitments leaves sufficient available quota on every balance-change boundary. Incoming leased quota can be leased onward only while it remains available for the entire period.
3. New leases use positive whole birds. Fractional amounts, same-party transfers and missing dates are rejected; existing allocation fractions remain unchanged.
4. Partial returns, early termination and corrections are not invented: saved new leases cannot be edited/deleted. An approved correction workflow is a follow-up.
5. The lessor chooses an existing Active owning registration if several exist. Incoming quota is account/type-level, with no invented lessee registration assignment. Allocation registration subtotals remain allocation evidence; the account net position includes the lease overlay.
6. Capacity is verified against the ledger known when the lease is saved. Later allocation changes, status changes, or direct external database writes require operational review; their existing write behavior is not changed by this task. No future balance can be guaranteed against later authorized ledger changes.
7. All current established flock report quota bases remain as implemented (including their existing Egg Production denominator). No non-Egg business rule is invented.
8. New-lease as-of activity rows are active-period projections; the saved original and its audit/history remain accessible after expiry. Existing historical allocation/lease transaction behavior is unchanged.

### Schema and read queries (text only; never executed here)

`sql/02_core_tables.sql` includes the new nullable field for fresh installations. `sql/32_quota_transaction_method_20261119.sql` provides the existing-installation draft:

```sql
ALTER TABLE EFNS_DEV.CORE.QUOTA_TRANSACTION
    ADD COLUMN IF NOT EXISTS TRANSACTION_METHOD VARCHAR(20);
```

Review/apply separately before enabling new lease entry in Snowflake. Allocation entry still omits the new field. If the field is absent, new lease entry rejects with a clear schema-update message and does not write.

Only new-lease persistence adds reads. With configured database/schema names, they are:

```sql
SELECT QUOTA_TRANSACTION_ID FROM EFNS_DEV.CORE.QUOTA_TRANSACTION
 WHERE QUOTA_TRANSACTION_ID=%s;
SELECT * FROM EFNS_DEV.CORE.QUOTA_REGISTRATION WHERE QUOTA_ID=%s;
SELECT * FROM EFNS_DEV.CORE.QUOTA_REGISTRATION WHERE QUOTA_TYPE IN (%s /* bound aliases */);
SELECT * FROM EFNS_DEV.CORE.QUOTA_TRANSACTION
 WHERE OWNER_ACCOUNT_ID=%s OR RELATED_ACCOUNT_ID=%s;
SELECT ACCOUNT_ID FROM EFNS_DEV.CORE.ACCOUNT WHERE ACCOUNT_ID IN (%s,%s);
SELECT UPPER(TARGET_ID) AS TRANSACTION_ID,
 LOWER(TRIM(RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) AS TRANSACTION_STATE
 FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW
 WHERE SOURCE_ENTITY=%s AND UPPER(TARGET_ID) IN
 (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))));
```

Values and alias lists are bound. RAW evidence is limited to the relevant transaction IDs. There is no new repository read interface or connection. Report reads reuse existing methods; the hidden usage context reads registrations for incoming lease type resolution only when a new lease is present.

### Protected files changed

| File | Narrow reason |
|---|---|
| `data/quota_lease_persistence.py` (new) | Validate whole-period availability and write a new lease under the unchanged continuity boundary. |
| `data/repositories/mock.py` | Route new leases through validation and block changes/deletion of saved leases; preserve allocation writer. |
| `data/repositories/snowflake.py` | Allow the nullable method field, route new leases through atomic validation/write, and block saved-lease changes/deletion. |
| `data/record_safety.py` | Reject revisions of saved/new-method lease rows; other entities and allocation revisions retain their existing path. |

## Verification

Synthetic tests cover dates/year boundary, conservation, several commitments, future ledger changes, inclusive expiry, invalid inputs, unknown state, adjusted utilization, outside-period identity, plain direction exports, authorization denial, idempotency, mandatory audit rollback, two-session lock reuse and real page creation. Existing fixture expectations are not changed. Full-suite counts and byte hashes are recorded below after execution.

No real names, producer quantities, exports or legacy files were added. No Snowflake calls, DDL execution, deployment or PR.

### Shipped-file byte proof against fetched main

| Shipped file | Before SHA-256 | After SHA-256 |
|---|---|---|
| `app/pages/8_Quota_Transactions.py` | `ccc3808a8afb35fba9ee6a9915c54059af5239035db35b56eaac3c6bab022af3` | `60b780a3f25f156c62d3f6b9f202022d692899788449eb6f58aa5128c4f4ea7a` |
| `app/services/quota_lease_entry.py` | `NEW` | `317815d069b283fd05fbe867a85433d359400aa8450f0bc06da968e542e383a1` |
| `app/services/quota_reports.py` | `899d73a0a0f0e56d1c0f0f733dd8c7a0b52c7537765da62baa08cf0a11401971` | `40085ff6e31afb49b4dbdd28a414ba49d77b8fc4afa5d6fcc7700055ec777a39` |
| `app/services/quota_usage.py` | `49b9ecad80315a49aaf72b1ca7ca84636612e0f4d3a944ef63962eba98af8248` | `d38d45ed90b856860a52c9ec7928b7ff69f1dc4acb6a80dd8f507ec437b9862d` |
| `data/confirmed_quota_position.py` | `2651a20e2025fb3196faffcbbc3a99dd38ab1e676c6dc6dbe702047910243c1e` | `a897495664724ab0101bf735b22a3c42bae816f5ac9da3bf13d97c7c3207fb55` |
| `data/quota_lease_persistence.py` | `NEW` | `42738cc97e8bb5fb1b045e35fb0c820e701e69bb1e0c50c9b098c9148fb97e70` |
| `data/quota_leases.py` | `NEW` | `3b01905f7b738df888fab8d85422a423e73b776e42e32247ecc71d9a6bbae7cb` |
| `data/quota_position.py` | `fb25c77e0ef28b20e571e916ffc5237bbd6ace5fdc840f81e1c35d7b72608db2` | `c20e28d61472cf41c5a4c4bb5a471a91052e23fbfbff4942feeeabdfc45d2867` |
| `data/record_safety.py` | `24d0ca02707582b9f0f98e132bb3438329afd017fa0fa57dca29baef1010b9a3` | `3092c3eb15260c673474e726de2929fbac955fcea14e5fe2c3d2b24b8db30879` |
| `data/repositories/mock.py` | `290190b38ddf439c32b52add6313bf20072c7eb6061772546a6c529a241fb653` | `029f40236fc40ac78a151c174f5dc4b87cfaa94369bd93f251282406d6130164` |
| `data/repositories/snowflake.py` | `442e35ca4158383cc274ae10bb65de88bfb1f4390c2c3d4266351bc0a66a2d70` | `4af1c3fcbeab77b5d6c13456442a1ea92f29ace076ec0c80c50d9c9e1621cd0e` |

11 shipped files changed/added; all 111 other shipped files are byte-identical. No shipped file was removed.

### Full-suite results and changed-file inventory

| Suite | Base | Final | Failures |
|---|---|---|---|
| Release, Python 3.12 | 2,274 passed, 1 skipped | 2,298 passed, 1 skipped | 0 |
| Root, Python 3.11 | 706 passed | 706 passed | 0 |

Final release run: 647.73 seconds. Final root run: 188.39 seconds. The 24 added cases are synthetic; no existing test or expected legacy value was changed. Existing fixture tests and outside-period equality checks pass. The live manifest contains 135 candidate LF SHA-256 entries, all regenerated from the final file contents.

Exactly 16 release files changed across the two commits:

- `app/pages/8_Quota_Transactions.py`
- `app/services/quota_lease_entry.py` (new)
- `app/services/quota_reports.py`
- `app/services/quota_usage.py`
- `data/confirmed_quota_position.py`
- `data/quota_lease_persistence.py` (new)
- `data/quota_leases.py` (new)
- `data/quota_position.py`
- `data/record_safety.py`
- `data/repositories/mock.py`
- `data/repositories/snowflake.py`
- `sql/02_core_tables.sql`
- `sql/32_quota_transaction_method_20261119.sql` (new, review-only DDL)
- `tests/test_quota_leases.py` (new)
- `docs/codex_reports/FLOCK_SUMMARY_QUOTA_LEASE_20261119.md` (new)
- `DELIVERY_RUNTIME_DIFF_20261030.json`

Part D commit: `7f1da66` (documented calendar gate). Part E is a separate implementation commit. No other branch/worktree, existing allocation writer, connection/authentication/lock implementation, report inventory rule or stored data was changed. No deployment or PR was created.
