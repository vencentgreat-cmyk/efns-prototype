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

## Decisions still required

1. How is Issuance calculated?
2. Is 0.400 mortality a fixed configuration, a report parameter, or a calculated value?
3. Does the as-of date use active Flocks, Quota Registrations, Quota Transactions, or all three?
4. Which Farm Location or address should appear when an Account has multiple locations?
5. Does Fax belong to Account, Farm Location, or another source?
6. Which records count toward the Producer total?

The current Quota Summary choices are provisional and intentionally confined to
the unambiguous rules described above.
