# Snowflake DEV Smoke Test

Use synthetic data only. Record the Snowflake query ID and UTC time for failures.

## Load the reviewed synthetic fixture

After the DEV tables and reporting views from `sql/02_core_tables.sql`,
`sql/03_production_tables.sql`, and `sql/04_reporting_views.sql` exist, load the
connected fixture with a CLI connection that can use `SYSADMIN`:

```powershell
snow sql --connection efns-dev --filename sql/09_dev_synthetic_seed.sql
```

The script inserts only deterministic `DEV_SYNTH` records and can be run more
than once without duplicates. Review all three result sets at the end: actual
counts must equal expected counts, and every broken-relationship and repository
semantic-mismatch count must be zero.
It creates 5 accounts, 8 facilities, 12 flocks, 20 flock transactions, 6 quota
registrations, 10 quota transactions, 10 salmonella tests, one synthetic import
batch, and 100 production records. It does not create application users, audit
events, raw EIMS rows, or security objects.

If the fixture was loaded by an older revision with the fixed
`2026-01-01 00:00:00` timestamp, run the targeted cleanup before loading it
again. The idempotent seed deliberately does not overwrite an existing row's
creation timestamp.

To remove only the fixture and other deliberately `DEV_SYNTH`-prefixed records,
run the dependency-safe cleanup script:

```powershell
snow sql --connection efns-dev --filename sql/10_dev_synthetic_cleanup.sql
```

All cleanup verification counts must be zero. Both scripts use a transaction
with an exception handler that rolls back on failure. Neither script changes a
schema or uses `DROP` or `TRUNCATE`.

## Checks

1. **Deployment runtime:** immediately after deployment, run
   `sql/08_post_deploy_grants.sql`. Inspect the Streamlit object and confirm
   `RUNTIME_NAME` is `SYSTEM$WAREHOUSE_RUNTIME`, the application starts, the
   runtime supplies Python 3.11, and Streamlit reports version 1.52.2.
2. **Connection and viewer identity:** open System Status as each test user,
   confirm the repository is Snowflake, authentication is Snowflake viewer, the
   displayed viewer email is correct, and `Check connection` succeeds.
3. **Authorization:** verify Admin, Data Editor, Reporting Viewer, and Developer
   navigation and direct-page guards against the documented permission matrix.
   Confirm an inactive `APP_USER` cannot enter the application.
4. **Reads and record navigation:** open Accounts, Facilities, Flocks, Quota,
   Salmonella, Production, and Reports. Apply filters, select a row, and use
   View. Confirm detail/edit remains inside the registered page, Back clears the
   selection, no new browser tab opens, and a deleted/stale Account returns to
   the list with a warning.
5. **Creates/updates:** as Data Editor create and update one synthetic Account,
   Facility, Flock, Quota, and Salmonella record. Create a Flock with Estimated
   Disposal Date, Permit Date, Date Ordered, Placement Date and Disposal Date
   unset. Confirm each optional DATE is SQL `NULL`, not the text `None`/`NaT`,
   and the save succeeds. Verify new IDs and UTC `CREATED_AT`/`UPDATED_AT` values
   against `CURRENT_TIMESTAMP()`. Confirm the UI shows the corresponding
   `America/Halifax` time and timezone label. Update the record and confirm
   `CREATED_AT` is unchanged while `UPDATED_AT` advances. Attempt a stale edit
   from a second browser and confirm the first saved value is not overwritten.
6. **Permission enforcement:** as Reporting Viewer attempt New/Edit actions and
   service mutations. Confirm the repository rejects writes. Confirm only an
   Admin can manage users and only Admin/Developer can read audit events.
7. **Production import:** upload a small synthetic workbook containing blank
   numeric cells and a comma-formatted number such as `1,234.50`. Verify one import
   batch, source rows, normalized rows, source hash, and `UNMATCHED` status.
   Confirm blank numeric cells are SQL `NULL`, `FLOCK_AGE` is NUMBER-compatible,
   and the comma-formatted value retains its numeric value.
   Re-upload it and confirm duplicate detection blocks it unless override is used.
8. **Rollback:** use a deliberately invalid non-empty numeric value in a
   normalized DEV row. Confirm the batch, RAW rows, and normalized rows all roll
   back and the UI identifies only the field and source row, without showing the
   uploaded value.
9. **Audit:** verify create, update, delete, import, and user-management events
   contain the actual `st.user.email` and a UTC `OCCURRED_AT` timestamp. For any
   failure, record the sanitized operation, entity, query ID, error code and
   SQLSTATE shown by the app; confirm no bound value or credential is displayed.
10. **Cost/operations:** confirm X-Small size, 60-second auto-suspend, resource
   monitor assignment, query warehouse, event logging, and no plaintext secrets
   in the stage or Streamlit source.
