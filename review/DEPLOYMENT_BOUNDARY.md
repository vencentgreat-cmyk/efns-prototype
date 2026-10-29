# Candidate and rollback preparation — no deployment performed

This candidate is an expanded application directory at `final_delivery/deployment_candidate` (82 runtime files). `final_delivery/runtime_diff.json` lists all differences against the 76-file readable saved-live rollback (`final_delivery/saved_live_rollback`). No runtime file was removed. The 5 additions include the earlier verified `quota_usage.py`/`flock_quantity.py` plus this round's `form_safety.py`, `business_time.py`, `record_safety.py`; 23 files differ. SQL/DDL, mapping, privileges and business data were not changed in this round.

The candidate's `app/security.py` SHA-256 equals the saved `zero_count_revision` deployment baseline. The separately expanded `final_delivery/independent_review` disables four prototype seed hashes and **must not be deployed**. Protected date repair/R1, source trace, navigation, 40053 transaction supplement and light theme files were checked against the saved runtime manifest. The `review/PROCESSING_MATRIX.md` and `VALIDATION_RESULTS.md` explain behavior and limits.

## Future authorized deployment checklist (not executed)

1. Read current company identity and live source hashes with the existing company read-only verifier. Compare against the saved 76-file rollback; if live has drifted, rebuild the candidate from that live version before proceeding. Do not assume the October 28 snapshot is still current.
2. Confirm the existing `EFNS_DEV.RAW.INTAKE_LOCK` has exactly one `continuity` row and the existing app role can access `APP.RECORD_REVISION`/`APP.AUDIT_EVENT`. No new permanent schema or grant is included here. If any prerequisite is absent, stop; do not run an initialization script merely to make deployment pass.
3. Preserve fresh live source/permission snapshots. From the **deployment candidate directory only**, use the company connection/role:

   ```powershell
   Set-Location 'C:\Users\Egg Farmers\Desktop\efns\efns-prototype\.local\review_fixes_20261028\final_delivery\deployment_candidate'
   snow streamlit deploy efns_dev --connection efns-company --authenticator SNOWFLAKE --role EFNS_DEV_DEPLOYER --replace --prune
   ```

4. If the organization's standard post-deploy process requires its existing `sql/08_post_deploy_grants.sql`, run **only after** a successful application deployment from the verified current project SQL file, with the agreed role. This task did not inspect/execute a fresh company permission change; grants must be reviewed before execution.
5. Re-run read-only live source hash/identity/readiness and test the browser. Use clearly marked test data only under separate authorization. Check create/edit/retry, stale Count reload, staged production re-review, delete protection and report filter rejection.
6. If deployment or verification fails, stop writes and use the fresh live backup, or the saved rollback only if its hash still matches the pre-deploy live source. Do not deploy the scrubbed review directory. Record the application version and rollback outcome.

Windows Application Control may block `snow.exe`; use the company-approved CLI path or the established Snowsight deployment route, not an unapproved bypass.
