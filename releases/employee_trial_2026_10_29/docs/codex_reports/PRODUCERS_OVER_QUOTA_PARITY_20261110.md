# Producers Over Quota parity — 2026-11-10

Base: `origin/main` **b60e5da**. Branch: `codex-poq-parity-fixes-20261110`, in a
separate worktree. The Sara branch/worktree is untouched. No Snowflake access,
SQL execution, stored-data update, PR or deployment was performed.

## Findings reported before logic changes

The attached legacy CSV contains **47 flock rows / 24 producers**, whereas the
initial PDF only showed the over-quota subset. The old >100% inclusion rule was
wrong. The local DEV exports reproduce the reported total **1,059,266** exactly:

`1,052,372 + 5,174 (40366) + 1,863 (40369) - 34 (40371) - 109 (40395)`.

The two supposed estimated disposal dates are actually the values stored in the
DEV export's **DISPOSAL_DATE** column. The report already prioritizes that column
correctly. Missing actual dates must not be invented in a runtime report.

## Item status

| Item | Status | Result |
|---|---|---|
| 1. Producer filtering | **Fixed** | All Accounts with a positive confirmed quota supplied by the existing owner-position helper are listed. At/below 100% remain visible; only the Account Total % Quota cell above 100% is red, in UI and PDF. Producers with Quota counts the listed Accounts. |
| 2. Disposal | **Data gap; current precedence is not a report bug** | Both saved DEV DISPOSAL_DATE values are 2026-11-30. The legacy actual dates/quantities are missing from these CORE fields. Regression tests prove actual dates on/before the report date exclude both flocks, and future actual dates override estimates. No runtime date override or new transaction interpretation was introduced. |
| 3. Missing 40407 / future flocks | **Data/source gap for 40407; future-zero logic is not a bug** | Nine of ten legacy future flocks exist in the DEV report export. 40407 is absent from that export; available CORE extracts are incomplete, so its absence from the live table or exclusion due to STATUS cannot be established. A previously supplied Bayview source fixture retains it at Inventory 0. |
| 4. Dates | **Data gap / not a report bug** | 40406 is already 2027-03-02 in the CORE export; the DEV report already has 40398 at 2026-12-08. No report timezone conversion or placement calculation causes these values. Preserve them. Another established difference is 40375 disposal 2027-03-22 versus legacy 2027-05-27. |
| 5. Notes | **Fixed** | All nonempty calculation notes appear in one collapsed `Calculation notes (N)` expander. PDF keeps its Notes section. |

## Disposal evidence and missing source rows

`tests/fixtures/flock_disposals/Untitled 2_2026-11-09-0841.csv` is a saved DEV CORE
field extract, already committed before this task:

| Permit / Account | EST_DISPOSAL in DEV | DISPOSAL_DATE in DEV | BIRDS_DISPOSED in DEV | Actual date / quantity in legacy |
|---|---|---|---|---|
| 40366 / 7159 | blank | 2026-11-30 | NULL | 2026-09-24 / 5,196 |
| 40369 / 7402 | 2026-10-05 | 2026-11-30 | NULL | 2026-10-08 / 1,851 |

Thus the existing actual-otherwise-estimated helper includes both as current on
10 November, and prints **the stored actual-column value**, not a chosen estimate.
The saved CORE data needs review of exactly `FLOCK.DISPOSAL_DATE` and
`FLOCK.BIRDS_DISPOSED` for these two permits. The correct legacy values above
come from the user and legacy disposal fixture; they are not substituted into
runtime inputs. The origin of the erroneous/later CORE values (old source state,
post-migration legacy edit, or earlier mapping) cannot be proven without the
corresponding raw migration rows/history.

The available `...0853.csv` transaction extract covers seven other permits;
it does not establish whether either target has a disposal-related transaction.
The report export supplies latest Count/Delivery observations, not complete
transaction histories. A complete CORE.FLOCK_TRANSACTION extract for the two
FLOCK_IDs is needed to check that question. Current transaction entry types are
Count, Delivery, Removal and Sale (`data/constants.py`); neither a Removal nor
Sale is assumed to mean final disposal. PENDING flock-stock rules are untouched.
No evidence-backed alternate actual date was found in the available transaction
or RAW exports. This is not a claim that such a row cannot exist in live DEV.

### Reports affected by the same source fields

Directly uses current-flock Inventory: Flock Current, Flock Current by Producer,
Flock Age, Flock Status, Flock Status by Producer, Producers Over Quota and Flock
Salmonella Testing Schedule. They share the current inclusion/effective-disposal
helpers and therefore inherit these two source-date problems; the saved DEV
Flock Current, Flock Age and Flock Status exports demonstrate inclusion.

Scheduled Flock Placements and Flocks Needing Counts also share lifecycle date
checks, so erroneous dates can affect their scope (their additional filters may
exclude these particular old flocks). Flock Disposals reads the same actual
column and consequently dates these records in November rather than September/
October. Flocks Counted is historical Count activity, not current Inventory, and
is not changed. No other report calculation is modified in this task.

## Future flock comparison

These are existence checks against **saved exports**, not a database query.
CORE extract = `DEV_FutureFlocks.csv` (nine selected layer/pullet rows).
Report extract = `DEV_FlockCurrent.csv` (all exported rows, including subtotals).

| Legacy Account / Permit | Legacy placement | Exists in saved DEV report? | Exists in limited CORE extract? | DEV placement / Inventory |
|---|---|---|---|---|
| 7038 / 40407 | 2027-01-19 | No | Not covered | Unknown from these exports; earlier supplied Bayview fixture has 2027-01-19 / 0 |
| 7050 / 40397 | 2026-12-03 | Yes | Not covered | 2026-12-03 / 0 |
| 7078 / 40404 | 2027-02-08 | Yes | Yes | 2027-02-08 / 0 |
| 7101 / 40399 | 2026-12-21 | Yes | Not covered | 2026-12-21 / 0 |
| 7113 / 40406 | 2027-03-01 | Yes | Yes | 2027-03-02 / 0 |
| 7168 / 40405 | 2027-02-15 | Yes | Yes | 2027-02-15 / 0 |
| 7172 / 40400 | 2026-12-14 | Yes | Not covered | 2026-12-14 / 0 |
| 7172 / 40401 | 2026-12-28 | Yes | Not covered | 2026-12-28 / 0 |
| 7173 / 40403 | 2027-02-01 | Yes | Yes | 2027-02-01 / 0 |
| 7178 / 40398 | 2026-12-07 | Yes | Not covered | 2026-12-08 / 0 |

40407 was already absent from Flock Current, before this report's grouping/filter.
Bayview is over quota, so the previous >100% Account filter does not explain that
missing flock. To resolve it in live data requires the 40407 FLOCK row including
FLOCK_ID, ACCOUNT_ID, STATUS, FLOCK_QUOTA_TYPE, HATCH_DATE, PLACEMENT_DATE,
EST_DISPOSAL and DISPOSAL_DATE, plus its Count/Delivery rows. A missing row and
an existing row rejected by current eligibility cannot be distinguished from
these limited extracts. No fixture-only flock is injected into runtime data.

## Date handling review

`flock_current_report.day` takes the stored date component with Timestamp.date;
it does not localize/convert a timezone. The read repository returns stored
FLOCK fields; the report does not add 19 weeks or derive placement from hatch.
The migration mapper reads source PLACEMENT_DATE as a date and assigns it to
PLACEMENT_DATE, independently of hatch. Nothing in this report explains the two
one-day differences. Inspecting the original source/RAW PLACEMENT_DATE values
and normalization history is needed to establish their upstream cause. No
unconfirmed correction was made. Across all matched report rows the only
placement/disposal differences are precisely 40406, 40398 and 40375 above.

## Fixture provenance and strict parity checks

- `legacy_reports/EIMSProducersOverQuota.csv`: exact attached EIMS export. Date
  is 10 November 2026, Egg Production, mortality 0.400; 47 detail rows / 24 Accounts.
- `producers_over_quota/DEV_FlockCurrent.csv`: exact local downloaded
  `flock_current_report (2).csv`. It supplies exported Counted/Count Date/Hatch Date
  and placement/effective disposal observations; runtime Inventory is recalculated
  by the real shared builders at 2026-11-10, not copied from its Inventory column.
- `producers_over_quota/DEV_FutureFlocks.csv`: exact local downloaded
  `Untitled 2_2026-11-09-0833.csv`, corroborating four future layer rows.
- Existing disposal CORE export supplies distinct actual/estimated fields where
  covered. Elsewhere only the report's effective date is known; the fixture does
  not claim to identify its original actual/estimate column.
- Account IDs/Flock IDs in the test adapter are registration/permit identifiers
  used only to join fixtures, not claims about live GUIDs. Active status follows
  the Flock Current export's scope. Quotas reuse the existing validated 24-owner
  fixture totaling 1,027,985. No Count is reverse-solved from an inventory value.

The row-by-row test compares **Reg No / Permit No / Inventory / % Quota** across
all 47 legacy rows with the real shared builders. Its exact allowlist is:

| Difference | DEV-derived calculation | Legacy |
|---|---|---|
| Extra 7159 / 40366 | 5,174 / 12.04% | Excluded: actual disposal data gap |
| Extra 7402 / 40369 | 1,863 / 104.08% | Excluded: actual disposal data gap |
| Missing 7038 / 40407 | Missing source row in report extract | Future flock / 0 / 0.00% |
| 7168 / 40371 | 40,524 / 73.45% from Count 2026-10-02 | 40,558 / 73.51% with newer 2026-11-03 Count |
| 7168 / 40395 | 19,550 / 35.44% from Delivery 2026-06-04 | 19,659 / 35.63% with newer 2026-11-03 Count |

No blanket tolerance or silent skip is used. Every other matched numeric row
must be identical. All 24 Account Totals are compared, with differences only for
7159/7402 (disposal data gaps) and 7168 (newer Counts). Nine available future rows
are checked at Inventory 0 / blank Last Count. Separate date comparisons allow
only the three exact differences above.

A **test-only** copy sets the two user-confirmed actual dates. It proves the
already-existing helper excludes them and produces **1,052,229 = 1,052,372 - 143**.
Without repairing the source fields, this build correctly still reflects
**1,059,266**, not the desired post-repair total. No runtime date/permit blacklist
or business-data edit is included. No claim of complete live CORE/RAW parity is made.

## Presentation and retained rules

CSV/XLSX keep numeric values and existing columns. Positive-quota producers with
no current flocks remain listed with Total Inventory 0; genuinely unknown totals
remain blank and noted. Missing/zero quotas are excluded with reasons. The
provincial metrics retain the Flock Status basis except Producers with Quota,
which now counts the listed producer Accounts. Shared mortality, Count/Delivery,
whole-week hatch age, future Inventory 0, actual-over-estimate precedence and
true-Count-only Last Count are unchanged.

An exact, unrounded total/quota comparison marks only over-quota Total percentage
cells. At exactly 100% no red is applied; a positive excess that rounds to
100.00% is still flagged. Detail percentages are not coloured. The UI uses a
Styler; PDF uses the same result-row marks and red Paragraph style. Other PDFs
are unaffected. The PDF quantity allowlist remains Inventory plus the four
existing summary counts. Calculation notes are deduplicated, collapsed by
default in UI, and retained in the PDF Notes section.
