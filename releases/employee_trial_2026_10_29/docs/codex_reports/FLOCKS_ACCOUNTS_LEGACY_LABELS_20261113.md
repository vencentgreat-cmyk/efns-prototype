# Flocks and Accounts legacy labels — 2026-11-13

Branch: `codex-flocks-accounts-legacy-labels-20261113`. Base: fetched `origin/main`, `5e6b167fc7fd2e665114c400e52a211b519e2fd5`, including Facilities labels PR #32.

## Display and field availability

Flocks default order: **Flock Quota Type, Permit Number, Registration Number, Account, Facility Name, Location, Bird Count, Placement Date, Flock Colour, Hatch Date, Estimated Disposal Date, Disposal Date, Comments, Disposal Plant, Hatchery, Breeder, Created On**, then the existing extra **Flock Number, Status**. No existing data column is removed. Flock Number and Permit Number remain separate: they are separate stored fields, even when their values happen to coincide.

Accounts default order: **Registration Number, Account Name, Address 1: Street, Address 1: City, Address 1: State/Province, Address 1: ZIP/Postal Code, Main Phone, Primary Contact, Breeder, Grader, Hatchery, Producer, Created On, Modified On**, then the existing **Account Email, Status**. Account Email is retained without pretending it is the primary contact's email.

The source row order, filter expressions, widget keys/options, selected-row ID arrays, related-record identifiers and links, forms' save payloads, validation and permissions are unchanged. Timestamp formatting and its existing timezone-unverified qualifier are preserved. Related-record tables keep the same rows/columns/order; only header configuration changes. Details field values are untouched. SQL, repositories, reports, calculations and export helpers are byte-identical.

| Legacy column | Existing source | Result / limitation |
|---|---|---|
| Flock Quota Type, Permit Number, Bird Count, Placement Date, Hatch Date | FLOCK.FLOCK_QUOTA_TYPE / PERMIT_NUMBER / BIRD_COUNT / PLACEMENT_DATE / HATCH_DATE | Direct read-only display |
| Flock Colour | FLOCK.EGG_COLOUR ← new_flockcolour_displayname | Label only; stored egg-colour field/options unchanged |
| Estimated Disposal Date, Disposal Date | FLOCK.EST_DISPOSAL / DISPOSAL_DATE | Stored dates only; no effective-date or fallback calculation |
| Comments, Disposal Plant, Hatchery, Breeder | FLOCK.COMMENTS / DISPOSAL_PLANT / HATCHERY / BREEDER | Direct stored text |
| Flock Registration Number, Account | Linked ACCOUNT.REGISTRATION_NUMBER / ORGANIZATION_NAME | Existing get_accounts lookup; no mutation |
| Facility Name | Linked FACILITY.FACILITY_NAME | Existing get_facilities lookup; existing unassigned behavior retained |
| Location | FACILITY.FARM_LOCATION_ID → FARM_LOCATION.LOCATION_NAME | **User confirmed this meaning.** Existing get_facilities/get_farm_locations only; no direct Flock field. Missing Facility/location link yields a dash. |
| Account registration, name, street/city/province/postal, phone | ACCOUNT.REGISTRATION_NUMBER / ORGANIZATION_NAME / ADDRESS_LINE1 / CITY / PROVINCE / POSTAL_CODE / CONTACT_PHONE | Direct stored values; address labels use the user's closest readable wording |
| Primary Contact | ACCOUNT.CONTACT_NAME ← primarycontactidname | Stored primary-contact name; no name matching or contact-selection algorithm |
| Email (Primary Contact) | **No explicit primary-contact email field or primary-contact ID link on ACCOUNT** | Missing confirmed account-to-primary-contact email association. ACCOUNT.CONTACT_EMAIL maps from account emailaddress1 and is labelled Account Email. CONTACT.EMAIL and PRIME_CONTACT exist, but choosing an associated contact would need a confirmed uniqueness/selection rule; no guessed join or fallback is added. |
| Breeder, Grader, Hatchery, Producer | ACCOUNT role Boolean fields | Values unchanged; visible role labels omit technical _ROLE suffix |
| Created On / Modified On | CREATED_AT / UPDATED_AT | Same timestamp formatter; no timezone conversion changes |

Evidence: `config/eims_migration_mapping_v3.json` ACCOUNT and FLOCK field maps; `sql/10_EIMS_V3_DEV_Deployment.sql` ACCOUNT, CONTACT, FACILITY, FARM_LOCATION and FLOCK definitions; existing repository reads. All requested Flock columns have direct or confirmed linked equivalents. The only unconfirmed/missing exact Account equivalent is **Email (Primary Contact)**. No live data was inspected. Truncated legacy address-header wording is not independently verified; the supplied readable names are used, with “Street” meaning stored ADDRESS_LINE1 only.

## Before / after labels

| Location | Before | After |
|---|---|---|
| Flocks list | PERMIT_NUMBER | Permit Number |
| Flocks list | BIRD_COUNT | Bird Count |
| Flocks list | HATCH_DATE | Hatch Date |
| Flocks list | EGG_COLOUR | Flock Colour |
| Both lists | STATUS | Status |
| Flocks list / Summary | Facility | Facility Name |
| Flocks filter | Egg colour | Flock Colour |
| Flocks Summary / form / Details | Egg Colour | Flock Colour |
| Flocks form | Facility * | Facility Name * |
| Flocks Details | Est Disposal | Estimated Disposal Date |
| Flocks Details | Account Id / Facility Id / Flock Id / Quota Id / Facility Detail Id (when present) | Account ID / Facility ID / Flock ID / Quota ID / Facility Detail ID |
| Both detail audit captions | Updated On | Modified On |
| Accounts list | CITY | Address 1: City |
| Accounts list | PROVINCE | Address 1: State/Province |
| Accounts list | POSTAL_CODE | Address 1: ZIP/Postal Code |
| Accounts list / Summary / form | Email | Account Email |
| Accounts Summary / form | Phone | Main Phone |
| Accounts form | Address 1: Street 1 | Address 1: Street |
| Accounts detail subtitle | Registration | Registration Number |
| Related Records and matched production grids | Raw SQL column names | Readable per-column labels; exhaustive schema-key matrix below |

Previously hidden legacy fields added to the default lists are additions, not renamed source data. Primary Contact is also displayed read-only in Account Summary. Existing Account Name, Registration Number, Main Phone in the Account list, Created On, Comments, date form labels and other already-readable labels stay unchanged.

## Export and navigation scope

The two pages have no explicit CSV/XLSX buttons. **User confirmed that Streamlit's built-in table download may follow the new visible columns.** Report Center CSV/XLSX fields, values and outputs stay unchanged. Raw DataFrame column keys are retained; column_config supplies display labels. IDs remain available where previously shown in Related Records/Details, with readable ID labels, and selected-row lookup still uses the original IDs.

The shared `related_records_table` takes an optional column_config argument, default None. Only Flocks opts into it here; all other callers retain their existing rendering and navigation. Accounts' local related-table renderer receives labels directly. There are no new repository methods or SQL statements; the Flock list adds one existing get_farm_locations read, not per-row reads.

## Validation and shipped bytes

Full release suite (Python 3.12): **2,159 passed, 1 skipped, 0 failed**, 707.81 seconds. Full root suite (Python 3.11): **706 passed, 0 skipped, 0 failed**, 145.15 seconds. Focused new-label/related-navigation/staff-workflow tests: **25 passed**. Commands: `python -m pytest -q` from each directory with separate worktree-local `--basetemp` paths. Tests use synthetic fixtures and both entrypoints (`streamlit_app.py`, `app/Home.py`): exact legacy order/labels, unchanged values/source frames, Location link and missing links, account versus primary-contact email distinction, filters, selected record, edit/save, related-record navigation and original Report Center CSV/XLSX columns/values.

Artifacts snapshot: 116 existing shipped files before; 117 after, because the new label-only service is included by the existing app/services/*.py wildcard. **113 existing shipped files are byte-identical**. Three existing shipped files change and one is added:

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| app/pages/5_Flocks.py | 92be24fbdf467004a1db6777af14a44149ac086cbb1cf62a5f9426a387677fa8 | 3e3a960db93ecfa6ddca61f349e1871fa3cd79affe434c2ba4b0e34df33bb1f6 |
| app/pages/3_Accounts_Facilities_Flocks.py | 3405c92c03b89f19595ce9563aa7fdd93fe9af0284bbb16f6225817a14842523 | e17ff0477d9338a27f8873e7bfaa05e559818e6ad674f07ff1284dc840b65e7e |
| app/navigation.py | 711e9624c9e5f47aae0c5a7ff980ca2216e5785c2442420f5adf7bda7769c321 | 9acc4d991bdc51ef3ad2c18dda970ade12027cbbc101907561f7e9b5d80e5b36 |
| app/services/legacy_view_labels.py | NEW | da13ec2e8bd1790dc3d25c7c73323eb1383f687cb0fda1ec02638ade18bbd5a1 |

All expanded snowflake.yml artifacts plus streamlit_app.py, environment.yml and .streamlit/config.toml are covered. No dependency, asset, config, schema, SQL, repository or data changes. No real-data files, Snowflake calls, deployment or PR. The live runtime-diff manifest retains main's entries and **110 candidate hashes** are regenerated from final LF-normalized bytes.

## Schema-key label matrix

The matrix lists readable header labels for existing repository schema keys that can appear in these pages' Related Records/matched-production grids. These grids preserve their previous column subsets. For the Flock Details Field column, the old label was the key converted to title case; only the semantic overrides and ID capitalization above differ. Flock colour applies only to Flock lists/Details; matched Production retains Egg Colour. Unknown future keys follow the same readable rule: underscores to spaces, title case, trailing Id to ID.

| Before (raw header) | After (readable header) |
|---|---|
| ACCOUNT_ID | Account ID |
| ACTIVATION_DATE | Activation Date |
| ADDRESS_1 | Address 1 |
| ADDRESS_2 | Address 2 |
| BARN_IDENTITY | Barn IDentity |
| BIRDS_DISPOSED | Birds Disposed |
| BIRDS_HOUSED | Birds Housed |
| BIRD_COLOUR | Bird Colour |
| BIRD_COUNT | Bird Count |
| BIRD_STRAIN | Bird Strain |
| BREEDER | Breeder |
| CAGE_BRAND | Cage Brand |
| CASE_FILE_NUMBER | Case File Number |
| CITY | Address 1: City |
| CLOSURE_DATE | Closure Date |
| COMMENTS | Comments |
| CONSTRUCTION_DATE | Construction Date |
| COUNT_SOURCE_LABEL | Count Source |
| CRACKS | Cracks |
| CREATED_AT | Created On |
| CREATE_DELIVERY_TRANSACTION | Create Delivery Transaction |
| DATE_INSTALLED | Date Installed |
| DATE_ORDERED | Date Ordered |
| DATE_RECEIVED | Date Received |
| DATE_RESULT_SENT | Date Result Sent |
| DESTRUCTION_DATE | Destruction Date |
| DETAIL_NAME | Detail Name |
| DETAIL_TYPE | Detail Type |
| DISPOSAL_DATE | Disposal Date |
| DISPOSAL_METHOD | Disposal Method |
| DISPOSAL_PLANT | Disposal Plant |
| EFFECTIVE_DATE | Effective Date |
| EGG_COLOUR | Egg Colour |
| EGG_TYPE | Egg Type |
| EIMS_FACILITY_DETAIL_ID | Eims Facility Detail ID |
| EIMS_LOCATION_ID | Eims Location ID |
| END_DATE | End Date |
| EST_DISPOSAL | Estimated Disposal Date |
| EXTRA_LARGE | Extra Large |
| FACILITY_DETAIL_ID | Facility Detail ID |
| FACILITY_ID | Facility ID |
| FACILITY_NAME | Facility Name |
| FACILITY_QUOTA | Facility Quota |
| FACILITY_TYPE | Facility Type |
| FARM_GATE_SALES | Farm Gate Sales |
| FARM_LOCATION_ID | Farm Location ID |
| FAX | Fax |
| FLOCK_AGE | Flock Age |
| FLOCK_ID | Flock ID |
| FLOCK_NUMBER | Flock Number |
| FLOCK_QUOTA_TYPE | Flock Quota Type |
| FLOCK_TRANSACTION_ID | Flock Transaction ID |
| GRADER_ACCOUNT_ID | Grader Account ID |
| GRADER_NAME | Grader Name |
| GRADER_NUMBER | Grader Number |
| GRADE_B | Grade B |
| GRADE_C | Grade C |
| HATCHERY | Hatchery |
| HATCH_DATE | Hatch Date |
| HEIGHT | Height |
| HIGHEST_BIRDS_PER_CAGE | Highest Birds Per Cage |
| HOUSING_SYSTEM | Housing System |
| INACTIVE_DATE | Inactive Date |
| INSPECTOR | Inspector |
| INVOICE_DATE | Invoice Date |
| INVOICE_NUMBER | Invoice Number |
| JUMBO | Jumbo |
| LARGE | Large |
| LEAKERS | Leakers |
| LEGACY_REJECT_LOSS_TOTAL | Legacy Reject Loss Total |
| LENGTH | Length |
| LOCATION_NAME | Location Name |
| LOSS | Loss |
| MANURE_DISPOSAL | Manure Disposal |
| MARKETING_TYPE | Marketing Type |
| MATCH_CONFIRMED_AT | Match Confirmed At |
| MATCH_CONFIRMED_BY | Match Confirmed By |
| MATCH_STATUS | Match Status |
| MEDIUM | Medium |
| NEST_RUN | Nest Run |
| NEST_RUN_17_PLUS | Nest Run 17 Plus |
| NEST_RUN_18_PLUS | Nest Run 18 Plus |
| NEST_RUN_19_PLUS | Nest Run 19 Plus |
| NEST_RUN_20_PLUS | Nest Run 20 Plus |
| NEST_RUN_21_PLUS | Nest Run 21 Plus |
| NEST_RUN_22_PLUS | Nest Run 22 Plus |
| NEST_RUN_23_PLUS | Nest Run 23 Plus |
| NEST_RUN_24_PLUS | Nest Run 24 Plus |
| NEST_RUN_25_PLUS | Nest Run 25 Plus |
| NET_BOXES | Net Boxes |
| NET_PER_BOX | Net Per Box |
| NET_WEIGHT | Net Weight |
| NOTES | Notes |
| NUMBER_OF_CAGES | Number Of Cages |
| NUMBER_OF_SAMPLES | Number Of Samples |
| ON_FARM_CONSUMPTION | On Farm Consumption |
| OTHER_LEVIABLE | Other Leviable |
| OTHER_NON_LEVIABLE | Other Non Leviable |
| OWNER_ACCOUNT_ID | Owner Account ID |
| PEEWEE | Peewee |
| PERMIT_DATE | Permit Date |
| PERMIT_NUMBER | Permit Number |
| PHONE | Phone |
| PLACEMENT_DATE | Placement Date |
| POSTAL_CODE | Address 1: ZIP/Postal Code |
| PRICE | Price |
| PRODUCER_ACCOUNT_ID | Producer Account ID |
| PRODUCER_NUMBER | Producer Number |
| PRODUCTION_ID | Production ID |
| PROVINCE | Address 1: State/Province |
| PULLET_GROWER | Pullet Grower |
| QUANTITY | Quantity |
| QUOTA_COUNT | Quota Count |
| QUOTA_ID | Quota ID |
| QUOTA_LEASE_TYPE | Quota Lease Type |
| QUOTA_NAME | Quota Name |
| QUOTA_TRANSACTION_ID | Quota Transaction ID |
| QUOTA_TYPE | Quota Type |
| RECORD | Record |
| REGISTRATION_NUMBER | Registration Number |
| REJECTED | Rejected |
| REJECTS | Rejects |
| RELATED_ACCOUNT_ID | Related Account ID |
| RELATED_QUOTA_ID | Related Quota ID |
| RELATED_TRANSACTION_ID | Related Transaction ID |
| RENOVATION_DATE | Renovation Date |
| REPORTING_WEEK | Reporting Week |
| REPORTING_YEAR | Reporting Year |
| SALMONELLA_TEST_ID | Salmonella Test ID |
| SMALL | Small |
| SOURCE_ROW_NUMBER | Source Row Number |
| SOURCE_TYPE | Source Type |
| SOURCE_WEEK_CODE | Source Week Code |
| SQUARE_INCHES | Square Inches |
| STATUS | Status |
| SUBTOTAL | Subtotal |
| TESTING_DATE | Testing Date |
| TEST_RESULT | Test Result |
| TEST_TYPE | Test Type |
| TOTAL | Total |
| TOTAL_ACCEPTED | Total Accepted |
| TOTAL_RECEIVED | Total Received |
| TRANSACTION_DATE | Transaction Date |
| TRANSACTION_TYPE | Transaction Type |
| UPDATED_AT | Modified On |
| WIDTH | Width |
