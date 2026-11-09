# Printable forms: sources and limitations

Base: `codex-trial-readiness-20261109`, `a1ad6f1`. No Snowflake connection, SQL execution, deployment or business-data changes.

## Layout and wording

The three original PDFs and the supplied logo screenshot are preserved in `tests/fixtures/legacy_forms/`. The runtime PNG is extracted from the identical logo embedded in the legacy licence PDF, avoiding the screenshot's black window border. Runtime assets are packaged by `snowflake.yml`; fixtures are not deployed.

`app/services/printable_form_text.py` centralizes fixed PDF wording and the header fill RGB values extracted from the originals. Existing spelling, including **complaince**, is retained. Licence and Salmonella forms use Letter portrait; the permit uses Letter landscape. Helvetica is used in place of the legacy Arial font. Paragraph wrapping and pagination accommodate longer source data; this is a reproduction of the layout, not a byte-identical legacy export. Permit column headers use the requested light-blue fill, as do the section headings.

## Field sources

| Form / fields | Existing source |
| --- | --- |
| Licence category, renewal type, report date, quota type | User parameters; Producer and Renewal defaults |
| Account name, registration | ACCOUNT.ORGANIZATION_NAME / REGISTRATION_NUMBER |
| Mailing address | ACCOUNT.ADDRESS_LINE1/2/3, CITY, PROVINCE, POSTAL_CODE; no additional mailing address is inferred |
| Primary contact, phone, email | ACCOUNT.CONTACT_NAME / CONTACT_PHONE / CONTACT_EMAIL; these are the existing Primary Contact fields, not an arbitrary CONTACT row |
| Confirmed quota | Existing confirmed_quota_position at report date and quota type, using existing transaction-state evidence helper; unavailable evidence leaves it blank |
| Grading station / pullet grower | ACCOUNT.GRADING_STATION_ACCOUNT_ID / PULLET_GROWER_ACCOUNT_ID joined to ACCOUNT.ORGANIZATION_NAME |
| Spent Fowl Plan | ACCOUNT.SPENT_FOWL_PLANS_ACCOUNT_ID joined to Account name; otherwise preserved SPENT_FOWL_PLANS text |
| Barn name, facility type | FACILITY.FACILITY_NAME / FACILITY_TYPE belonging to the selected Account |
| Barn address / location | FACILITY.FARM_LOCATION_ID -> FARM_LOCATION.ADDRESS_1/2, CITY, PROVINCE, POSTAL_CODE; no fallback to the owner's address |
| Permit, hatch/placement dates, birds, colour, breed | FLOCK.PERMIT_NUMBER / HATCH_DATE / PLACEMENT_DATE / BIRD_COUNT / EGG_COLOUR / BIRD_STRAIN |
| Permit account name / registration | FLOCK.ACCOUNT_ID -> ACCOUNT |
| Hatchery | Selected pullet FLOCK.HATCHERY text, unchanged |
| Salmonella facility | SALMONELLA_TEST.FLOCK_ID -> FLOCK.FACILITY_ID -> FACILITY.FACILITY_NAME |
| Sample date, result, comments | SALMONELLA_TEST.TESTING_DATE / TEST_RESULT / COMMENTS |
| **Date Result** | **No confirmed source. Blank. DATE_RECEIVED and DATE_RESULT_SENT are not assumed to be laboratory result dates.** |
| Signatures and signing dates | Intentionally blank lines for completion by the applicant |

Every unavailable selected-record value is blank and disclosed in the app. Available fields with missing records/links are distinct from a schema-wide absent source. The app lists missing Account Name, Mailing Address, Primary Contact, Phone, Email, Grading Station, Spent Fowl Plan, Pullet Grower, confirmed quota, Barn Name, Facility Type, Barn Address, permit registration/account/date/bird/colour/breed/barn/location fields, Hatchery, Facility, Sample Date or Sample Result when applicable. Optional Comments are blank when absent; signature lines remain blank by design.

## Confirmed selections and remaining conventions

- User-confirmed pairing: layer `4NNNN` pairs with pullet `3NNNN` and optional letter suffixes, including `40403` -> `30403`, `30403a` and `30403b`. The selector offers one matching Pullet Number or All matching pullet permits (default). A note appears immediately when no match exists. Unrelated permits and duplicate permit records are rejected with a clear message. No relationship is written.
- User-confirmed filter: Pass accepts stored Pass/Negative; Fail accepts Fail/Positive. The app labels these SE Not Present and SE Present and offers All (default). Stored result text is printed unchanged.
- Sample dates are inclusive. The date filter is optional, so historical records are not excluded by a guessed default window.
- Licence barn rows retain all recorded facilities owned by the selected Account; no unrequested active/status filter is invented.
- Birds in the permit are the stored FLOCK.BIRD_COUNT. This does not change the Delivery-based Placed rule in Flock Disposals.

## Runtime dependency and reads

`environment.yml` now declares `reportlab=5.0.0` in the existing Snowflake channel. Availability was verified on 2026-11-09 in Snowflake's public Linux package index at <https://repo.anaconda.com/pkgs/snowflake/linux-64/repodata.json.bz2> (including Python 3.10–3.14 builds). The same version is installed for local tests. This confirms package availability and declaration, not live environment installation; Snowflake was not accessed. `pypdf` is a local test/extraction dependency only. Both local pins are declared in `requirements-review.txt`.

Existing repository reads: `get_accounts`, `get_facilities`, `get_farm_locations`, `get_flocks`, `get_salmonella_tests`, `get_quota_registrations`, `get_quota_transactions`. The licence reuses the existing `get_inactive_quota_transaction_ids` helper. **No SQL or repository methods were added or changed.**

Salmonella Testing Letter remains **Not included in this trial**.
