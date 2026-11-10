# Producers Over Quota Report — 2026-11-10

## Scope and source

New report only: `producers-over-quota`, Flock group, Available, VIEW_REPORTS,
CSV/XLSX/PDF. No existing builder, calculation, query or report output is changed.
The supplied three-page `tests/fixtures/legacy_reports/EIMSProducersOverQuota.pdf`
is copied byte-for-byte from the attachment. Its header is interpreted as
**10 November 2026**, Egg Production, mortality **0.400 percent per month**.
The PDF contains **32 flock rows and 16 Account Total rows**.

Runtime uses the existing repository reads and `load_flock_report_quotas` in
`app/pages/4_Reports.py`: confirmed Egg Production owner positions at the report
date, including `get_inactive_quota_transaction_ids`. No SQL/read method was added
and no Snowflake connection, data change or deployment was performed.

## Rules and evidence

| Rule | Evidence / status |
|---|---|
| Use the exact Flock Status inclusion scope: Active flocks, effective disposal strictly after report date or empty; actual disposal takes precedence over estimated disposal. Special Permit is excluded, including All. | Existing shared builders; explicitly confirmed by user because the PDF cannot establish excluded rows. Account status/producer flags are not given a new filter. |
| Classify an Account using the sum of its known flock Inventory values, not individual flock percentages. Include only when the unrounded total is strictly greater than confirmed quota. Exactly 100% is excluded. | User confirmation. All 16 PDF totals agree with this rule and the supplied quota-provider figures. |
| Unknown detail Inventory stays blank, is disclosed, and does not discard an otherwise qualifying Account. Missing/zero quota excludes only that Account with a named reason. A total with no known inventory cannot be classified and is disclosed. | User confirmation; empty/NULL/partial-total tests. |
| Reuse Flock Current's Count/Delivery observation, Count conflict handling, exact monthly mortality and floor-to-whole-birds inventory. Do not use FLOCK.BIRD_COUNT as an inventory observation. | Existing validated builders are called directly. No mortality or quota formula is reimplemented. |
| Future placements show current Inventory 0; an as-yet-uncounted flock with a known placement date also displays 0 in this new legacy projection. Missing placement, invalid quantities and conflicting placed Counts remain genuinely unknown. | User confirmation of not-yet-counted zero versus unknown. This projection does not change Flock Current, Flock Age or Flock Status. The provincial summary still comes unchanged from Flock Status. |
| Flock Age uses the shared whole-week age from HATCH_DATE to report date, including future placements; it is not weeks from Placement Date. | Existing Flock Current/Flock Age calculation. Known hatch 2026-09-08 for 40407 gives age 9 on 2026-11-10 despite placement 2027-01-19. The PDF omits hatch dates for other future flocks, so their ages alone cannot independently prove a rounding convention. |
| Last Count shows the selected observation date only when it is a true Count and the flock is already placed. Delivery fallback and future placements have blank Last Count, even if a future placement has a recorded Count. | User confirmation. The PDF leaves 40402 and all seven future placements blank. No Delivery date is relabeled as a Count date. |
| Placement Date, Disposal Date and Last Count use DD/MM/YYYY. Disposal uses the shared actual-otherwise-estimated rule. | PDF layout, shared helper and export round-trip tests. |
| Per-flock % Quota and Account Total % Quota use the existing Decimal, two-decimal HALF_UP utilization helper. Inventory is summed before computing the total percentage. | All 32 PDF row percentages and all 16 totals match. For example Bayview detail percentages sum to 102.47%, whereas its correctly recomputed total is 102.46%; displayed percentages are not summed. |
| Sort Accounts by numeric Registration Number (text and blank registrations remain safe), then flocks by Permit No. Show Reg No/Account Name on the first detail row and a Total row after each Account. | PDF ordering/layout. NULL labels remain blank. |
| Province summary covers the full Flock Status population, including under-quota Accounts; it is not recomputed from the filtered over-quota table. | The PDF's 1,052,372 provincial inventory exceeds the sum of its 16 listed Account totals. Shared summary equality is tested. |
| Retain confirmed Egg Production quota as the denominator/allocation for non-Egg flock filters, exactly as Flock Status does. Show a note that only Egg Production is legacy-validated. | Explicit user confirmation; no new non-Egg quota rule. |

Header: `For <Quota Type> as of <DD/MM/YYYY> at <mortality> Mortality`.
Mortality has at least three decimals; extra entered precision is retained.
Parameters default to today in America/Halifax, mortality 0.4, and Egg Production.
PDF uses the existing shared header/logo/blue table/footer, plus the five summary
lines above the table. CSV/XLSX contain the same ten table columns and displayed
dates as the on-screen table. Formula-safe exports, export permission and audit
use the existing `downloads` and PDF helpers.

The PDF-only quantity allowlist is `Inventory`; the separate summary allowlist is
`Inventory Birds`, `NFPMC Allocation`, `Issuance for Province`, and
`Producers with Quota`. Reg No, Permit No, Flock Age and % Quota are not grouped.

## Fixture validation and limits

Tests extract the legacy PDF text with pypdf and compare all 16 Account Total
inventory/percentage pairs, plus all 32 per-flock inventories/percentages, using
an explicitly labeled **output-projection fixture**. Those tests mock already
calculated flock observations; they do **not** claim to reconstruct missing
flock data or source Count quantities from a rounded inventory number.

Independent source-backed tests use the previously supplied observations:

| Account | Result as of 2026-11-10 | Source-calculation evidence |
|---|---|---|
| 7038 | Total 16,550; 102.46%. Flocks 40368 = 9,823 / 60.82%; 40382 = 6,727 / 41.65%; 40407 = 0 / 0.00%, age 9. | Existing Bayview hatch/placement/Count/Delivery fixtures; matches the PDF. |
| 7159 | Total 45,646; 106.20%; flock 40394 age 23. | Existing Count 45,773 dated 2026-10-20 and hatch/placement fixture; matches the PDF. |
| 7402 | Total 1,941; 108.44%; flock 40402 age 20; Last Count blank. | Existing Delivery 1,979 dated 2026-06-18 and hatch/placement fixture. Effective disposal display date comes from the PDF, not a newly verified DEV field. |
| 7113 | PDF/output-projection total 33,513; 120.97%, including 40406 at Inventory 0. | Raw Count quantities and hatch-date source fixtures for 40365/40380, and the source record for 40406, are unavailable. Full source-calculation parity cannot be asserted. |
| 7173 | PDF/output-projection total 250,352; 106.57%. | Existing 40362 observation can explain that flock, but source Count quantities for 40372/40386/40393 are absent; the full Account cannot be reconstructed. |
| Remaining listed Accounts | Account totals and row percentages match the output-projection fixture. | No claim of complete source Count/hatch/placement evidence. |

The reused quota-provider fixture has 24 expected positions totaling 1,027,985;
the new report does not hardcode those positions. Runtime uses the confirmed
position function through the existing page helper. The limited source-flock
fixture cannot reconstruct provincial Inventory 1,052,372 or its full 102.37%
utilization. These summary values are verified as PDF specification values, while
the actual builder is separately tested to return exactly Flock Status's summary
for identical inputs. No missing flock or Count quantity was invented to force
full provincial parity.

### Snapshot differences

For Cornwallis (7113), the PDF projection covers the displayed inventories
16,815 (40365), 16,698 (40380), and 0 (40406), their percentages, and the Account
Total 33,513 / 120.97%. It cannot independently validate the source Count
quantities dated 2026-10-02 for 40365 and 40380, or HATCH_DATE for 40365, 40380
and 40406. Consequently their source-to-inventory mortality calculation and
source-to-age calculation are unverified. The missing source record for 40406
also prevents independent confirmation of its placement/disposal fields and
transaction history. These values were not fabricated. The user will compare
same-day exports from DEV and legacy after deployment; deployment is outside
this task.

No discrepancy is detected for the source-backed inventories and percentages
above. No new DEV snapshot was queried or supplied, so **no residual difference
can be positively attributed to DEV snapshot drift**. Unavailable source rows are
reported as an evidence gap rather than called a logic error or a proven snapshot
difference. Actual DEV/report parity for 7113 and the complete province remains
TBC pending matching source fixtures.

## Regression coverage

- Exact 100% excluded; a truly over-quota ratio that displays as 100.00% included.
- Mortality changes can change inclusion; existing calculations are reused.
- Missing/zero quota affects only the corresponding Account; reasons are shown.
- Partial known totals retain blank genuinely unknown details; not-yet-counted
  and future-placement zeroes are tested separately.
- True Count versus Delivery, same-day Count preference, future Count blanks.
- Empty/NULL data, inactive/disposed scope, Special Permit exclusion and non-Egg note.
- Source DataFrames remain unchanged; CSV/XLSX dates, formula escaping, PDF summary
  formatting and catalog-wide normal/empty/NULL/no-row/PDF smoke coverage.
