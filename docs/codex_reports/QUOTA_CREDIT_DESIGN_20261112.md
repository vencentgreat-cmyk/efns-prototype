# Quota Credit — proposed design

**Design only, 12 November 2026.** Reviewed against main `2c75cf9ea93ec919448571a39fdada3e8c5fda35`. This document proposes decisions for Sara; it does not confirm a new business rule. No code, SQL file, schema, data, test or manifest is changed. No Snowflake query or deployment was run.

The staff-facing name is **Quota Credit**, following the legacy term in the request. The legacy screen, its approval process and its exact reporting treatment have not been supplied. Those details remain unconfirmed. Technical references below are relative to `releases/employee_trial_2026_10_29/`, the released app, rather than the older root app.

## 1. What a Quota Credit does

A Quota Credit gives a producer an extra number of quota birds for a stated period. It belongs to a particular Quota Registration. It does not buy or sell quota, transfer quota to another producer, add birds to a flock, or change a flock's Count.

**Illustration only:** a producer has quota of 20,000 birds. Staff record a Quota Credit of 1,000 birds from 1 January to 31 March 2027. If approved for the report concerned, quota including the credit is 21,000 on both those dates and every date between them. From 1 April it returns to the producer's regular quota, which may itself have changed through ordinary quota transactions. Expiry does not create a negative Adjustment or remove the credit's history.

Recommended Quota Summary presentation: **Quota before Credits | Quota Credit | Issuance**. Issuance would be quota including the credit, with the caption “Issuance includes Quota Credits for the selected As of Date.” The two additional columns explain the difference from regular quota. This is a proposed future report change, not a change made by this task.

## 2. Current calculation and proposed report effects

### Confirmed behavior in the current code

`data/confirmed_quota_position.py:14`, `confirmed_quota_position`, calculates the owner's regular quota. It uses only the owner's own transactions on that owner's Active Quota Registrations of the requested Quota Type. Registration start/end dates are not an additional eligibility filter in this function. Inactive migrated transactions are excluded using RAW state evidence. Transactions without a RAW row are treated as Active under the existing policy; unavailable or contradictory evidence makes the result unknown.

For each registration it selects the latest eligible Active Base by Effective Date, then Created At. Older activity before that Base is excluded. Without an Active Base, all otherwise eligible activity is used. Adjustment retains its signed value; Base, Global Adjustment, Purchase and Lease (In) add; Sale and Lease (Out) subtract; Terminate Quota has zero effect. National/Provincial Allocation transactions are excluded. Effective Date must be on/before the report date; leases must not have expired. An unresolved Base tie or invalid required evidence produces unknown. **Credits must not alter any of these rules.**

`config/quota_rules.json` points to this confirmed calculation. `data/quota_position.py` also contains a separate, evidence-gated calculation used by the hidden `app/services/quota_usage.py` panel. It must not be mistaken for the Report Center calculation or re-enabled by this feature. `flock_stock` remains PENDING.

### Exact current entry points

| Page/report | Current modules and functions | Proposed treatment after Sara approves credits |
|---|---|---|
| Quota Summary | `app/pages/4_Reports.py` handler `quota_summary`; `app/services/report_center.py:164` `_quota_report_accounts`, `:221` `build_quota_summary`; calls `confirmed_quota_position` once per listed Account | Add the two explanatory columns above; Issuance and its total become regular quota plus eligible credits. Keep existing Account, Quota Type, Status and As of Date filters and one-row-per-Account behavior. Keep registration-date listing behavior unchanged. Count positive issuance within the existing listed-account scope. |
| Quota Summary Details | Same page, handler `quota_summary_details`; `report_center.py:234` `build_quota_summary_details`, using `per_type_sums` from the confirmed calculation | **No change to its transaction amounts or gross totals.** Credits are separate records, not Base/Adjustment/Purchase/Global Adjustment/Lease (In). Explain why its gross transaction total differs from Issuance including credits. A separate credit listing is a possible later addition. |
| Flock Status and Flock Status by Producer | `4_Reports.py:75` `load_flock_report_quotas`; `app/services/flock_age_report.py:22` `build_flock_age_quotas`; `app/services/flock_reports.py:70` `build_flock_status_report`, `:108` `build_flock_status_by_producer_report` | Proposed, subject to Sara: Account Quota and Util. use quota including credits. Inventory, Count, mortality, ages, placements and disposal rules do not change. Treat province allocation separately, as explained below. |
| Producers Over Quota | Same quota loader; `app/services/producers_over_quota_report.py:23` `build_producers_over_quota_report`, which also calls Flock Status for province metrics | Proposed, subject to Sara: use quota including credits for flock/Account % Quota and the red over-100% Account Total highlight. The report continues listing producers with quota, not just those over 100%. A previously zero-quota producer could become eligible while a credit applies; this needs business acceptance. Inventory and Last Count rules do not change. |
| Flock Age | `4_Reports.py` handler `flock_age`; `flock_age_report.py:63` `build_flock_age_report`, using the same quota map | If credits are approved for Flock Status utilization, apply the same Account Quota/Util. treatment here to keep the reports consistent. No change to bird calculations. |
| Quota Transaction entry/list | `app/pages/8_Quota_Transactions.py`; `data/constants.py:19`; repository `get_quota_transactions`, `upsert_quota_transaction` | **No new transaction type and no change to stored transaction amounts.** This page lists activity rather than computing the current confirmed balance. Its “Credit Type” control actually stores `QUOTA_LEASE_TYPE` (Fixed Term/Open Ended/Seasonal); it is not the requested Quota Credit feature. Do not reuse that field. |
| Quota Transactions and Leases reports | `app/services/quota_reports.py:121` `build_quota_transactions_report`, `:141` `build_quota_leases_report`; page handlers for transactions, leases and leases by end date | **No changes to rows, Bird Count, Price or totals.** They describe transactions/leases, not temporary credit records. |
| Quota History report | `quota_reports.py:175` `build_quota_history_report`; calls the confirmed calculation for adjustments, Running Balance and Current Quota | Keep its transaction rows, Running Balance and Current Quota on the regular transaction basis. Add an explanatory note once Summary includes credits. Do not invent opening/expiry transactions to make this ledger equal the credit-inclusive report. A separate credit summary could be requested later. |
| Scheduled Flock Placements, Flocks Counted, Flock Disposals | Builders in `flock_reports.py` receive the same quota map; `4_Reports.py:398` supplies the start date for placements and report/end date for the other two | **Keep their Quota fields on the regular basis in the initial proposal.** Changing a shared loader must not change these accidentally. Any later credit-inclusive quota must use that report's existing quota-reference date, not today's date or each individual row's date. |
| License Application Form | `app/services/printable_forms.py:90` `build_license_application` calls `confirmed_quota_position` directly; `build_printable_form` supplies RAW state evidence | **No change initially.** It continues printing regular quota until Sara confirms credits belong on a licence. Do not change it indirectly by changing the confirmed function's meaning. |
| Flock Current / by Producer, Salmonella schedule/tests/forms, Flocks Needing Counts, Production reports, Customize Report | Existing builders/raw-field reports; Flock Current uses `flock_current_report.py` without a quota balance input | **No numeric changes from a credit.** Quota Type labels, physical birds and stored fields remain unchanged. Customize Report does not acquire a credits dataset unless separately designed. |

Credit-inclusive figures must agree between the screen, CSV, XLSX and PDF for every report enabled for credits. Report/Export permissions and export audit logging continue to apply. Existing scope differences, including producer-role counting, must not be “cleaned up” as part of this feature.

**Allocation needs a separate decision.** Today Flock Age/Status derive NFPMC Allocation by summing supplied Account quotas; they do not read `CORE.QUOTA_ALLOCATION` for that number. Producers Over Quota reuses the Status summary. Replacing the quota map globally would therefore also increase NFPMC Allocation and alter Provincial Utilization automatically.

Recommended policy for Sara's approval: credits increase a producer's usable quota, but do not themselves increase NFPMC Allocation. Keep a **regular quota map** and a separate **quota-including-credits map**. Keep province NFPMC Allocation on its existing regular basis; Provincial Utilization remains Inventory Birds divided by that regular allocation. Province Issuance would sum quota including credits, while the by-Producer Status report's Issuance would be that producer's quota including credits. Account Util./% Quota would use the effective amount. Clearly explain the resulting allocation/issuance difference. If Sara chooses a different policy, settle it before implementation; do not silently make these labels interchangeable.

Flock report quota maps currently use **Egg Production** positions even for a different flock Quota Type selection. Preserve that existing basis: only Egg Production credits could affect those maps. Other quota types in Quota Summary would use only credits of that same type. Non-Egg Flock reporting must not be newly presented as legacy-validated.

### Exact current repository reads — descriptions only, not executed

There is no SQL quota-total query behind the current confirmed reports: the calculation is pure Python over repository results. In `data/repositories/snowflake.py`, current unfiltered report calls issue:

```sql
-- get_accounts, line 501
SELECT DISTINCT * FROM EFNS_DEV.CORE.ACCOUNT;
-- get_quota_registrations, line 624, through _filtered at line 482
SELECT * FROM EFNS_DEV.CORE.QUOTA_REGISTRATION;
-- get_quota_transactions, line 641
SELECT qt.* FROM EFNS_DEV.CORE.QUOTA_TRANSACTION qt;
-- Existing flock report inputs: get_flocks / get_facilities / get_flock_transactions
SELECT * FROM EFNS_DEV.CORE.FLOCK;
SELECT * FROM EFNS_DEV.CORE.FACILITY;
SELECT DISTINCT ft.* FROM EFNS_DEV.CORE.FLOCK_TRANSACTION ft;
```

When supplied, repository account/status/type/date filters use bound `%s` parameters. The transaction Account filter includes Owner **or** Related Account; the confirmed calculation subsequently restricts the owner. Report loaders call `get_quota_registrations()` without `active_only=True`; substituting that option would introduce a CURRENT_DATE-based registration filter and change historical behavior.

`app/services/quota_state.py:9`, `get_inactive_quota_transaction_ids`, performs this ID-scoped state read, binding `('QUOTA_TRANSACTION', JSON_of_transaction_IDs)`:

```sql
SELECT UPPER(TARGET_ID) AS TRANSACTION_ID,
       LOWER(TRIM(RAW_DATA:STATECODE_DISPLAYNAME::VARCHAR)) AS TRANSACTION_STATE
FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW
WHERE SOURCE_ENTITY=%s AND UPPER(TARGET_ID) IN
  (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))));
```

The older repository `get_quota_summary` method still projects `CAST(NULL AS NUMBER(18,2)) AS ISSUANCE` and filters registration dates. It is **not** the current `build_quota_summary` path and is not an appropriate credit integration point.

## 3. Proposed record and persistence model

Recommend a separate **`EFNS_DEV.CORE.QUOTA_CREDIT`** table rather than overloading QUOTA_TRANSACTION. It avoids changing Base cut-offs, transaction signs, gross totals and lease expiry behavior. Add credits after the existing confirmed calculation, once per owning Account/type, never once per flock or once per joined transaction row.

The following is a **draft only**, using the existing CORE UUID, NUMBER(18,4), DATE, VARCHAR and UTC TIMESTAMP_NTZ conventions. No DDL file is created or executed.

```sql
CREATE TABLE EFNS_DEV.CORE.QUOTA_CREDIT (
    QUOTA_CREDIT_ID VARCHAR(36) NOT NULL,
    QUOTA_ID VARCHAR(36) NOT NULL,
    OWNER_ACCOUNT_ID VARCHAR(36) NOT NULL,
    CREDIT_COUNT NUMBER(18,4) NOT NULL,
    START_DATE DATE NOT NULL,
    END_DATE DATE NOT NULL,
    REASON VARCHAR(2000) NOT NULL,
    COMMENTS VARCHAR(2000),
    CREATE_REQUEST_ID VARCHAR(100) NOT NULL,
    IS_DELETED BOOLEAN NOT NULL DEFAULT FALSE,
    DELETED_AT TIMESTAMP_NTZ,
    DELETED_BY VARCHAR(100),
    DELETE_REASON VARCHAR(2000),
    CREATED_AT TIMESTAMP_NTZ NOT NULL
        DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
    UPDATED_AT TIMESTAMP_NTZ NOT NULL
        DEFAULT CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,
    CREATED_BY VARCHAR(100) NOT NULL,
    UPDATED_BY VARCHAR(100) NOT NULL,
    CONSTRAINT PK_QUOTA_CREDIT PRIMARY KEY (QUOTA_CREDIT_ID),
    CONSTRAINT UQ_QUOTA_CREDIT_REQUEST UNIQUE (CREATE_REQUEST_ID),
    CONSTRAINT FK_QUOTA_CREDIT_QUOTA FOREIGN KEY (QUOTA_ID)
        REFERENCES EFNS_DEV.CORE.QUOTA_REGISTRATION (QUOTA_ID),
    CONSTRAINT FK_QUOTA_CREDIT_OWNER FOREIGN KEY (OWNER_ACCOUNT_ID)
        REFERENCES EFNS_DEV.CORE.ACCOUNT (ACCOUNT_ID)
);
```

| Field/group | Intended meaning and enforcement |
|---|---|
| QUOTA_CREDIT_ID | Stable UUID. Application generates it using the existing idempotent request/receipt approach; never use a displayed name as the key. |
| QUOTA_ID, OWNER_ACCOUNT_ID | Required links. Owner is derived server-side from the selected registration, displayed read-only and checked again inside the save. Quota Type is derived from that registration rather than duplicated in this table. |
| CREDIT_COUNT | Birds, not dozens or money. Recommend finite positive whole birds initially; NUMBER(18,4) matches quota storage and leaves a deliberate future option for fractional credits. Reject zero, negative, non-finite and out-of-range amounts; no floating-point arithmetic or silent rounding. Fractional allowance needs Sara's confirmation. |
| START_DATE, END_DATE | Required business dates, inclusive, with Start Date on/before End Date. A same-day credit is valid. No open-ended credit initially. DATE values must not shift through UTC conversion; default today's date from America/Halifax. |
| REASON, COMMENTS | Reason required for issuing a credit; Comments optional. Require a separate correction/cancellation reason for later changes. |
| CREATE_REQUEST_ID | Unique creation request, checked with a payload fingerprint in the history receipt. Retrying the same save returns the same record; reusing the request for different values is rejected. An identical-looking second credit is not an automatic retry. |
| IS_DELETED and deletion fields | Soft deletion means “Cancelled” to staff. Keep the row, dates and amount; record who cancelled it, when and why. Expiry never sets IS_DELETED. |
| Created/Updated fields | Server-supplied UTC audit timestamps and authenticated actor IDs; not editable form inputs. Actor IDs follow the existing history convention, not a new assumption about a particular authentication backend. |

Repository validation must enforce relationships, uniqueness, amount/date rules and permissions regardless of database key declarations. Register the model and date/numeric fields in the existing persistence layer; extend `data/repositories/base.py`, `mock.py` and `snowflake.py` together. Proposed interfaces: `get_quota_credits`, `get_quota_credit`, create/revise credit, and an explicit `cancel_quota_credit`. No direct page SQL and no client-controlled table names.

Batch reads should select only required credit columns and the registrations used by a report, using bound ID/date parameters; fetch once, not once per Account/flock. A successful empty result is evidence of zero credits; a failed/unavailable read is not. Only report result rows should reach the browser. Existing RAW transaction-state evidence remains separate from the new credit table.

Do not silently move issued credits if a registration's owner or type changes. Block those parent changes while credit history exists until an explicit reassignment/cancellation workflow is agreed. Prevent physical deletion of a linked Account or Quota Registration. This requires extending reference/parent guards; adding a table alone is insufficient.

## 4. Proposed staff workflow, permissions and Record History

**Entry location:** a **Quota Credits** section on the Quota Registration detail page, with **Add Quota Credit**. Quota Summary offers a **View Quota Credits** link/action for the producer; when several registrations exist, staff select the actual registration before entering anything. Keep Report Center primarily for reviewing reports rather than embedding a second independent edit form there.

Show Producer name/registration number, Quota Registration name/number and Quota Type as clear labels. Show the owner read-only. The editable fields are **Quota Credit (birds), Start Date, End Date, Reason, Comments**. Do not show UUIDs as the primary labels. Show credits as **Upcoming, Current, Expired, Cancelled**, derived from the dates/cancellation flag, plus their entered amount and who recorded them. No calculated background expiry writes are needed.

On save, recheck the parent, owner, quota type, dates, amount, permission and overlap rule on the server. Recommend accepting new credits only against an Active registration for its producer. Warn about a period outside recorded registration dates rather than inventing a new global registration-date rule. Changing a registration must immediately refresh the read-only owner before saving, following the corrected Quota Transaction owner pattern.

**Overlap proposal, not a confirmed legacy rule:** initially reject an overlapping non-cancelled credit for the same producer and Quota Type, even if it belongs to another of that producer's registrations. Overlap includes a shared end/start day. Different quota types are independent. Show the existing credit's dates/amount and let staff correct or shorten it rather than unknowingly duplicate it. If Sara permits multiple simultaneous credits, replace rejection with a clear combined-credit preview and explicit confirmation; the calculation would add them, not select the largest or latest.

Edit dates/amount with a correction reason and the original UPDATED_AT version. Reject stale saves and ask the user to reload. Do not allow editing the credit's owner/registration in place after issue. Show the affected dates/reports before accepting a backdated correction. Proposed initial permission is Admin-only for backdating and for issuing/changing credits generally.

Use **Cancel Quota Credit**, not physical deletion. For an entry made in error, cancellation voids it in recalculated reports, including past As of Dates. To end a genuine credit early while retaining its earlier validity, correct End Date rather than cancel it. This distinction and whether old reports should be restated require Sara's approval. Retain original values in Record History in either case; a current-row query is not an “as originally printed” archive.

| Action | Proposed initial authorization |
|---|---|
| View credit records | Existing VIEW_DATA, within the same accessible producer/registration scope. All four existing roles can currently view data. |
| Run reports / export | Existing VIEW_REPORTS / EXPORT_REPORT checks; no new export shortcut. |
| Add / edit | New MANAGE_QUOTA_CREDITS permission, initially Admin only, plus existing CREATE_DATA / UPDATE_DATA respectively. Data Editor's existing general write permissions must not automatically authorize credits. |
| Cancel | MANAGE_QUOTA_CREDITS plus DELETE_DATA, initially Admin only. Do not expose cancellation as an unrestricted generic update. Developer and Reporting Viewer remain read-only. |
| Approve | No approval mechanism is assumed to exist. If Sara wants a second person to approve, design Draft/Approved states, approver identity/time and separation of entry/approval before enabling entry; unapproved credits must have zero report effect. |

Enforce the credit-specific permission on generic create/revise routes as well as named credit methods; adding QUOTA_CREDIT to an entity registry must not let a Data Editor bypass the restriction through `revise_record`. Import and developer-tool routes must not provide an alternative unauthorized credit writer. Buttons alone are not the authorization boundary.

**History integration:** extend the explicit entity registries in `data/record_safety.py`, the repository MODEL and authorized method mappings, `app/services/form_safety.py` integration, and the entity/label choices in `app/pages/21_Record_History.py` and `app/services/revision_history.py`. The new staff label is **Quota Credit**. A record label can read “Quota Credit · producer registration · 1,000 birds · 2027-01-01 to 2027-03-31”, retaining the UUID only as its underlying value.

Use the current transactional pattern in `data/record_safety.py` (`create_once`, `revise_entity`, `history_audit`) and `data/repositories/continuity.py`: save the credit, its `APP.RECORD_REVISION` before/after snapshots, and its mandatory `APP.AUDIT_EVENT` in the same repository transaction. The change records include entity QUOTA_CREDIT, action, reason, request ID, actor and UTC recorded time. Failed mandatory history/audit must roll back the credit. Keep the existing Changed by name/email lookup and Halifax history display. Cancelled records must remain selectable in history; do not lose them through a default active-credit filter. Implement soft cancellation deliberately rather than calling the current physical-delete helper unchanged.

Proposed history kinds are CREATE, UPDATE and CANCEL, displayed as Created, Changed and Cancelled. For cancellation, AFTER_DATA contains the retained, cancelled row. Under the current `history_audit` mapping, CANCEL produces an UPDATE audit event; its details must identify logical cancellation explicitly. The action still requires the cancellation permissions above. A cancellation must not be logged as though a physical row deletion occurred.

Row version checks alone do not prevent two people creating overlapping rows at the same time. A future implementation needs a proven serialization strategy for the producer/type scope, with a repeat overlap check inside it. Confirm how the existing persistence/locking approach can support this before promising overlap prevention; concurrent-create tests are a release gate.

## 5. Proposed effective-quota rule

For producer A, Quota Type T and report date D:

1. Calculate **Q**, regular quota, with the existing confirmed function unchanged.
2. Take each distinct, non-cancelled credit linked to A's own Active registration of T, with **Start Date <= D <= End Date**. Apply approval eligibility too if an approval workflow is adopted. Do not treat registration effective/end dates as a new filter on regular transactions.
3. Add each eligible credit once to obtain **C**. Different registrations must not multiply a credit; Account and Quota Type matching must be validated. Credits are not limited by the latest Base date and are not absorbed into a later Base while their own period continues, unless Sara chooses otherwise.
4. **Quota including Credit = Q + C.** Use exact Decimal arithmetic. Zero verified credits gives exactly Q. Unknown Q stays unknown, even when C is known. Invalid/ambiguous credit evidence or an unavailable credit read makes the credit-inclusive amount unknown rather than pretending C is zero; regular quota can still be displayed separately.
5. After End Date, that credit contributes zero automatically for later report dates. A report for a date within its original period still includes it unless staff later correct or cancel it. No proration, mortality, carry-forward, negative expiry transaction or change to flock inventory is proposed.

With overlaps prohibited, only the permitted credit contributes in a producer/type period. If stacking is approved, C is the **sum of all distinct eligible credits**, including credits issued against different registrations of the same producer/type. There is no “latest wins” rule. A credit ending on 31 March and another starting on 31 March overlap; starting the second on 1 April avoids that overlap.

Implement the rule as a new pure calculation/context layered over `confirmed_quota_position`, returning regular quota, current credits, quota including credits and explanatory reasons. Do not redefine `net_position` or add Quota Credit to the transaction sign dictionary. Supply separate regular and effective maps to reports so unchanged reports and NFPMC Allocation cannot inherit credits accidentally. Retain each report's existing treatment of partial known totals and unknown values, with explicit notes for unavailable credit evidence.

The proposed target report effects in section 2 require Sara's approval before activation. A first rollout may show credits in Quota Summary only while the other report effects remain disabled and clearly identified; it must not imply cross-report agreement until the approved report set is enabled together.

## 6. Risk, effort and rollout

These are relative estimates, not a delivery-date commitment. Overall effort is **Large** because this adds a business entitlement write path with audit, permissions and concurrent editing, rather than just a report column.

| Part | Effort | Main risk / acceptance evidence |
|---|---|---|
| Agree terminology, workflow and report policy | Small | Legacy credit treatment is not yet confirmed; Sara signs off the example, overlap and allocation choices. |
| Table, model and bounded reads in mock/Snowflake | Medium | Parent identity, precision, absent-table handling and migration/grants/package coverage; test an empty verified table separately from unavailable evidence. |
| Create/edit/cancel, concurrency and mandatory history/audit | Large | Duplicate submissions, overlapping concurrent entries, unauthorized cancellation, stale versions or committed rows without audit; atomic failure and retry tests required. |
| Pure date-range/effective calculation | Medium | Inclusive endpoints, multiple registrations, Base changes, expiry, negative/zero/invalid amounts, exact precision and unknown evidence; zero-credit identity tests required. |
| Staff entry and review UI | Medium | Wrong producer/registration and cancellation versus early expiry; synthetic staff walkthrough and read-only-role tests. |
| Quota Summary and approved Flock report integration | Medium | Double-counting credits per flock, changing allocation unintentionally or inconsistent denominators; compare every affected figure and all three export formats. |
| Full regression, historical/reporting decisions and rollout | Large | Restated historical reports, accidentally changed untouched reports and incomplete legacy credit migration; baseline fixtures must still match with zero credits. |

Safe order for a separately authorized implementation:

1. Sara approves the questions below, including which reports and allocation figures may change. Record the chosen rules explicitly; this design is not that approval.
2. Obtain separate authorization for schema, protected write/auth/locking/history changes. This documentation task authorizes none of those edits.
3. Build the model/repositories, pure function and audit workflow against synthetic data. Start with an empty credit table and a dedicated credit feature switch **off**. Do not repurpose the existing confirmed quota rule flag or flock_stock PENDING setting.
4. Test boundaries (including leap days), expiry, same-day periods, overlaps/concurrent saves, duplicate retries, owner/type changes, cancellation, backdated corrections, unknown evidence and failure rollback. Run the full suites. Verify regular results and every existing report/export remain unchanged with no credits; verify no unapproved report changes even when credits exist.
5. Shadow-review regular quota, credits and proposed totals without replacing report numbers. Confirm legacy examples and permission/audit behavior. Do not bulk-convert Adjustments, leases or a field called Credit Type into credits; any legacy credit import requires a separately reviewed source and duplicate controls.
6. Enable the approved report set and Admin entry together, after the empty-table check confirms identical existing numbers. Only explicitly entered, eligible credits then alter approved figures. If approval is required, entry alone must not alter numbers until approved. Review the first credits with staff and reconcile totals in screen/CSV/XLSX/PDF.
7. Emergency rollback disables credit application/entry and returns reports to regular quota, retaining all credit/history rows. This intentionally changes any figures that already included credits, so announce and reconcile it; do not silently delete records. Resolve the issue before re-enabling.

## 7. Questions for Sara — business decisions before implementation

1. Should staff enter Quota Credits from the Quota Registration, with a link from Quota Summary?
2. Are credits always whole birds with both a Start Date and End Date, or are fractions or open-ended periods needed?
3. Should a credit stop counting automatically on the day after its End Date, without changing the producer's regular quota?
4. Should credits count in Flock Status, Flock Age and Producers Over Quota percentages while leaving NFPMC Allocation unchanged?
5. Can a producer have overlapping credits for the same Quota Type, with their bird amounts added together?
6. Which staff may enter, approve, change and cancel credits, including whether a second person must approve them?
7. When an old credit is corrected or cancelled, should past reports be recalculated or retained as originally issued?
8. Where should Quota Credits be shown or printed besides Quota Summary, including transaction history or licence forms?

**Scope check:** this branch adds only this Markdown design at repository-root `docs/codex_reports/QUOTA_CREDIT_DESIGN_20261112.md`. No implementation, SQL execution, test execution, manifest regeneration, deployment or PR creation is part of this change.
