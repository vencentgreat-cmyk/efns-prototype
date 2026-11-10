# Sara staff feedback fixes — 2026-11-10

## Base and scope

Branch `codex-sara-feedback-fixes-20261110` starts from updated main `b60e5da`,
including merged Producers Over Quota (`26d5b43`). Main advanced during testing;
the unpublished task branch was recreated on that base and the feedback changes
reapplied. No existing remote branch was changed, merged or rebased. All changes are within this release.
No Snowflake connection, SQL execution, data changes or deployment occurred.
No repository, auth, lock, import, quota-position or report calculation code was
modified. No transaction type or automatic flock date calculation was added.

## Quota Transaction owner

The Registration selector already lives in a rerunning container, not an
`st.form`. The disabled Owner Account text widget had a persistent key; its
initial value remained in session state when the registration changed.
It is replaced by read-only derived text. Counterparty controls are unchanged.
Before both create and edit saves, a fresh registration read checks the final
form-preserved payload's owner. A mismatch is rejected with a clear message;
no repository write is attempted. Existing repository write paths are unchanged.
Local UI tests cover registration changes, create/edit owner persistence and a
stale/mismatched owner rejected before saving.

## Bird Strain / Breed

There is one flock new/edit form, in `app/pages/5_Flocks.py`. It now selects
exact distinct nonblank stored BIRD_STRAIN values from `get_flocks()`, preserves
the current value even if absent from the source list, and offers Other with a
text input. Stored spelling, case and whitespace are not normalized or rewritten.
Both widget keys participate in the existing edit-preservation snapshot.

Distinct values found in the local seeded mock data: **Hy-Line, Lohmann,
Novogen** (`data/synthetic.py`). There are no existing bird-strain constants in
`data/constants.py`. DEV values were not queried. At runtime the dropdown uses
the connected repository's distinct existing values, not this three-value list.
Tests also cover unknown historical values, choosing a known value, Other,
saving a custom value, and a subsequent unrelated edit preserving it.

## Salmonella permit duplication (item 3)

This is a derived duplicate, not a second user-entered permit with different
meaning. The selector chooses FLOCK_ID. The form reads the selected flock's
PERMIT_NUMBER and copies it into SALMONELLA_TEST.PERMIT_NUMBER on save (a stored,
denormalized copy). The extra disabled Permit Number input has been replaced
by the caption **Selected flock permit (read-only)**. Storage behavior is unchanged.

## Production Data field sources

The selected rows and filters still come from `get_production_records` /
REPORTING.VW_PRODUCTION_SUMMARY. One existing `get_production_report_records`
read is now made only after a Reporting Year is selected. It spans the
minimum/maximum reporting week in the selected records and
supplies CORE.PRODUCTION_RECORD fields, joined by PRODUCTION_ID without changing
row count, original totals or source quantities. Empty selections skip this read.
No SQL or repository method was added. `get_accounts` supplies names and
registration numbers once per page run; there are no per-row repository reads.

| Display | Existing source / treatment |
|---|---|
| Producer identity | Existing producer identity helper; ACCOUNT_LINKED labels use ACCOUNT.ORGANIZATION_NAME and REGISTRATION_NUMBER. Raw PRODUCER_ACCOUNT_ID remains a separate source-ID column. Unlinked labels are unchanged. Missing linked Account details produce a clear label, not an invented name. |
| J, XL, L, M, S, PW, B, C | CORE.PRODUCTION_RECORD.JUMBO, EXTRA_LARGE, LARGE, MEDIUM, SMALL, PEEWEE, GRADE_B, GRADE_C. |
| NR, CR, OL, ON, RJ, LK, FG, FC | CORE.PRODUCTION_RECORD.NEST_RUN, CRACKS, OTHER_LEVIABLE, OTHER_NON_LEVIABLE, REJECTS, LEAKERS, FARM_GATE_SALES, ON_FARM_CONSUMPTION. |
| NR25 through NR17 | CORE.PRODUCTION_RECORD.NEST_RUN_25_PLUS through NEST_RUN_17_PLUS; these are the stored nest-run weight-band quantities, not inferred individual egg weights. |
| Housing System | CORE.PRODUCTION_RECORD.HOUSING_SYSTEM. No Facility-based housing inference is made. |
| Marketing Type / Egg Type | CORE.PRODUCTION_RECORD.MARKETING_TYPE / EGG_TYPE, displayed as stored. |
| Grading Station | GRADER_ACCOUNT_ID joined to ACCOUNT.ORGANIZATION_NAME, falling back to stored PRODUCTION_RECORD.GRADER_NAME. |

The existing normalized CORE.PRODUCTION_SIZE_BREAKDOWN table also has SIZE_BAND
and QUANTITY (`sql/03_production_tables.sql`), but the requested wide component
columns are already supplied by the existing CORE report read. This page does
not invent a pivot or new read of that separate table. Where the wide source
field is NULL or absent, the added cell remains blank; missing values are never
converted to zero or inferred from summary totals.

All requested field categories exist in the model. Their completeness in real
DEV data is unverified because no database access was made. No unsupported
housing type, breed, nest-run band or grading-station value was invented.

The table and CSV/XLSX exports use the same selected columns and rows, including
the new fields and the raw producer Account ID. Quantities retain stored decimal
precision; Production Management report rounding is not applied. Existing totals
are not recomputed. The requested Report Center navigation caption is included.
Tests compare the actual page table with both export input frames, test exact
fractional source values, and cover linked/unlinked/unknown Accounts and empty data.


## Production Data follow-ups

### Bounded detail loading

A Reporting Year is required before the extra `get_production_report_records`
read. Week alone may match the same week across every historical year and does
not enable this read. The caption says: "Select a Reporting Year to load detail
columns; use Week to narrow the results."

The original summary rows, coverage metrics and CSV/XLSX row sets are not capped.
Without Year, existing fields supplied by the summary repository remain visible,
producer labels still resolve to Account names, and no extra detail query runs.
With Year selected, the existing read is bounded by the selected rows' reporting
weeks; existing filters and calculation rules are unchanged. No SQL was added.

### Invalid detail identities

The page catches ValueError from detail loading/enrichment (including NULL or
duplicate detail PRODUCTION_ID), warns "Production details are unavailable;
showing original records. Filter or reload to try again.", and displays the
original unenriched rows using the existing identity helper. Source-scope filtering
still applies. Raw exception text is not displayed; unrelated exception types are
not swallowed. Tests exercise both invalid-identity cases through the real page.

### Actual CSV contract

Tests capture the actual Production Data CSV download, parse it, and compare its
row count, Production IDs and columns with the displayed table, with and without
a Year selection. They assert the exact stored fractional component `0.1250` and
stored TOTAL `24945.0000`, including a deliberate mismatch between source TOTAL
and the displayed components. No rounding, zero filling or total recomputation
is applied. Blank source values remain blank in the CSV.

### Local performance measurement

Full local seeded MockRepository dataset: **200 rows**, default seed 42. Median
of **11 warm paired runs**, alternating before/after order, using the same
repository instance. Measures the page's three summary reads, optional detail
range/read, Account read, identity/detail preparation and source-scope preparation.
It excludes dataset generation, Streamlit rendering, CSV/XLSX serialization and
network/database latency. Existing row IDs and totals were checked for equality.

| Unfiltered data load | Before (f5f7607 pipeline) | After |
|---|---:|---:|
| Summary/display/export source rows | 200 | 200 |
| Extra detail read calls | 1 | 0 |
| Extra detail rows loaded | 200 | 0 |
| Median time | 34.975 ms | 24.608 ms |

Measured local reduction: **29.6%**. This small synthetic local dataset cannot
establish DEV load time or network-query savings; no Snowflake access occurred.

Only the Production Data page, its follow-up tests, these notes and the integrity
manifest are changed in this follow-up. Other entry forms and report builders
remain unchanged.
