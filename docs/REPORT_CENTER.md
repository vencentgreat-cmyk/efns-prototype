# Report Center

The Report Center is an internal Streamlit workspace backed by the existing
authorized repository. It does not accept SQL, schema names, table names, joins,
expressions, or browser URLs. Report definitions and custom fields come from
code-maintained allowlists, and CSV/XLSX exports apply spreadsheet formula
protection to the exact displayed result.

## Implemented reports

`Quota Summary Report` is the first functional catalog report. Its row grain is
one Quota Registration. The repository applies Quota Type, Account, Status and
Quota Registration effective/end-date predicates before returning data. A
ranked Farm Location join chooses one address per Account: an Active location is
preferred, followed by the lowest `FARM_LOCATION_ID`. Account contact phone is
used only when the selected Farm Location has no phone. Fax currently comes from
Account.

The report displays the selected as-of date, Quota Type, an execution timestamp
in `America/Halifax`, distinct producer count, result count and the supported
columns. Producer count means distinct Accounts in the result whose current
`PRODUCER_ROLE` is true. Issuance and mortality are not calculated because the
repository has no confirmed formula or authoritative source for either value.

The existing `Salmonella Test Report` remains a dedicated registered Streamlit
page and is opened internally from the catalog.

## Catalog-only contracts

The following screenshot-supported names are cataloged but cannot yet run:

- Flock Age Report
- Flock Current Report
- Flock Current Report by Producer
- EIMS Salmonella Testing Form
- EIMS Salmonella Testing Letter
- EIMS License Application Form
- Flock Permit Form

The Flock reports need confirmed historical/as-of semantics. Forms and letters
provide safe stable-record selection but generation remains disabled until an
official source template is obtained. For each form or letter, obtain the
approved layout, wording, logo assets, page size, declarations, signature rules,
recipient/address rules, and one fully redacted example from Sara or the EIMS
provider.

## Customize Report

Authorized users can choose one of ten curated datasets, allowlisted fields,
supported relationship filters, date/status/type filters, column order,
grouping, sorting and field-specific aggregations. Repository methods apply
simple Snowflake filters server-side. Result shaping and approved aggregation
operate on the returned dataset. Configurations saved in this prototype live in
the current Streamlit session only and contain allowlisted settings, never SQL.

Application permissions distinguish `view_reports`, `use_report_builder` and
`export_report`. Report execution and exports are checked in service logic as
well as the page. Run, export and session-save actions create audit events.

### Flock record counts

Local correction prepared on 27 October 2026; not deployed by this change.
In `Customize Report`, select `Flocks` and group by `Facility ID` (optionally
also `Facility Name` for a readable label). `Aggregation field` defaults to
`Flock record count`, independent of numeric output fields. Each filtered Flock
record contributes one, even if Bird Count is NULL, zero or negative. This is
not a bird total, current occupancy or inventory calculation. Grouping by ID
keeps distinct facilities separate even when their names are identical.

Filters apply before counting, unassigned Facility groups remain unless filtered
out, and duplicate Flock IDs or duplicate parent keys still fail rather than
inflate counts. Grouped configurations without numeric aggregations, including
older saved Flock configurations, also return record counts. Removing Group by
returns detail rows; numeric aggregations retain their existing behavior.
Preview, CSV, XLSX and session-saved configurations share the same report result.
No database view, schema, repository write or permission change is required.
The reported company sample (six groups totaling 35) has local synthetic
regression coverage, not a fresh company DEV or browser acceptance in this task.

## Account roles in Flock-related reports

Report-only changes prepared locally on 9 October 2026:

- Flock and Flock Transaction results expose `FLOCK_ACCOUNT_ID/NAME` and
  `FACILITY_ACCOUNT_ID/NAME` separately. The Account filter means Flock Account.
- Production results retain `PRODUCER_ACCOUNT_ID`; the Account filter means
  Producer Account, independently of the Flock and Facility owners. Optional
  Flock Account and Facility Account filters can be combined with it.
- Facilities are looked up by their GUID, not by `(Account, Facility)`.
  All relationship lookups are left joins with many-to-one parent checks.
  Missing references stay visible unless excluded by an explicit filter;
  duplicate parent/primary identifiers raise an error instead of inflating sums.
- `REPORT_FACILITY_ID` is display-only. For production it uses the original
  production Facility reference when present, otherwise the referenced Flock's
  Facility. Neither the stored `FACILITY_ID` nor the producer reference is changed.
  A missing Producer Account is never filled from the Flock/Facility owner.
- Filtering precedes grouping; grouping precedes export. CSV and XLSX use the
  same displayed result, including null-role groups and signed quantities.
  Bird Count totals are Flock-record totals, not a verified live-stock formula.
  Do not sum Flock-level attributes across production observations.

The older joined report builder follows the same role distinctions. Its saved
generic Account fields on a production report now refer to the producer. Its
Salmonella Account remains the Test Account, with Flock/Facility roles separate.

`sql/04_reporting_views.sql` additionally exposes both Account roles on
`VW_FLOCK_DETAIL`, and changes the summary's Import Batch join to LEFT JOIN.
Size detail no longer needs an Import Batch join and takes year/week directly
from production, with SIZE_BREAKDOWN_ID exposed for child-grain checks. COPY
GRANTS preserves existing view grants when definitions are replaced. Views still
assume unique parent PK values; standard-table FK declarations alone do not
prove that assumption. App report joins check parent uniqueness explicitly.
The size-detail view is one size-breakdown row per production, not production
grain; its repeated production attributes must not be summed as observations.

No SQL was executed, no DEV data was read/written and no application deployment
was performed for the initial report-only change. The followup review did read
DEV metadata and aggregates, without executing updates. The view update must be applied in a
separately authorized deployment; local SQL tests are not Snowflake execution
evidence. This does not approve cross-Account entry/import: the six historical
Flocks and 57 dependent transactions remain pending, and all existing entry,
migration and correction validations are unchanged.

Production details/exports now include both original Facility IDs,
`REPORT_FACILITY_SOURCE` (Production record / Linked Flock / No available
reference) and `FACILITY_REFERENCE_DIFFERENCE` (Same reference / Different
references - review / Not comparable). A difference does not decide which
reference is wrong. A stored reference can still point to a missing parent;
source provenance is not a claim of relationship validation.

Production period filters use Reporting Year/Week from the production row,
never the Import Batch's period. Unknown periods stay unknown. Calendar date
ranges are disabled for production and rejected in saved service configurations
instead of being silently ignored; no week-to-calendar-date formula is invented.
`TOTAL` is exposed separately as Source Total, not substituted for Total Received.
Units/interpretation still need business confirmation; stored-value reconciliation
does not establish a business balance formula.

See [DEV read-only findings and deployment sequence](reporting_deployment_preparation.md)
and `sql/reporting_deployment_checks.sql` for before/after verification.

## Decisions still required

1. How is Issuance calculated?
2. Is 0.400 mortality a fixed configuration, a report parameter, or a calculated value?
3. Does the as-of date use active Flocks, Quota Registrations, Quota Transactions, or all three?
4. Which Farm Location or address should appear when an Account has multiple locations?
5. Does Fax belong to Account, Farm Location, or another source?
6. Which records count toward the Producer total?

The current Quota Summary choices are provisional and intentionally confined to
the unambiguous rules described above.
