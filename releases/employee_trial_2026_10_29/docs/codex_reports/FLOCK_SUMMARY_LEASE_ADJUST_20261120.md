# Task 5: Flock Summary and lease adjustments

Base: origin/main a4b0e35 (Task 3 merged); separate worktree and branch codex-flock-summary-lease-adjust-20261120. No live Snowflake, deployment, operational DDL or real-data files.

## Initial findings

- Migration parse_reporting_period splits YYYYWW; production_week uses REPORTING_YEAR*100+REPORTING_WEEK. Mapping v3 maps efc_productionweek to SOURCE_WEEK_CODE and EFCYear/EFCWkNumber to the calendar. No inconsistent date/ISO-week derivation is used for these report codes. Historical CYYWW remains an explicit supported legacy format, unrelated to EFC date resolution.
- Existing get_efc_dates reads CORE.DIM_EFC_DATE. The new resolver validates complete Sunday-Saturday weeks; Saturday is the inventory date, never a sum over time. Mock calendar is explicitly synthetic, not a new production calendar rule.
- Admin and Data Editor currently have CREATE_DATA; Developer does not. Part I requires a lease-only authorization route, preserving all other permissions and Admin-only void.
- Details currently includes positive legacy Lease (In) and omits legacy Lease (Out); legacy types/values must remain unchanged. New-method leases currently contribute only incoming amounts to Details.

## Part H

Flock Summary reuses Flock Status inventory for each EFC week end. Stock is never summed over weeks. Grouped rows use stable Account identity internally, then show Account and registration labels. Known inventory totals follow existing Status handling; unavailable values remain a dash and are disclosed. Quota-type columns are exhaustive for eligible types in the input, including an explicit Not specified category; Special Permit remains excluded exactly as Flock Status. Non-selected type columns show zero. Weeks without included flocks have no row.

Production resolves dates only from the maintained calendar; the synthetic mock fixture is generated for adjacent local years and is not evidence of any unexported production calendar dates. Empty/unknown calendars display a clear message. CSV retains the data columns; XLSX Notes and PDF include the Saturday caption.

Part H focused validation: 463 passed (builders, Report Center, all report smoke cases and PDF exports). No existing report fixture values were edited. Final full suites follow Parts I/J.
