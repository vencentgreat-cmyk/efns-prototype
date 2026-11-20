# Snowflake sign-in role mapping - 20 November 2026

Base: fetched origin/main `a4b0e35`, containing Task 3 `2f1d067`. Branch: `codex-login-role-mapping-20261120` in a separate worktree.

## Current identity, storage and permission enforcement

Before this task, `app/auth.py::current_user` reads `app/runtime.py::snowflake_viewer_email` (`st.user.email`) and resolves by email through `SnowflakeAuthStore.resolve_identity`. SECURITY.APP_USER stores USER_ID, EMAIL, DISPLAY_NAME, ROLE, ACTIVE and audit dates. There is no Snowflake-username mapping field. `app/snowflake_security.py` handles the existing user-management CRUD and APP.AUDIT_EVENT; local mode uses SQLite app_user, password sign-in and its existing sessions. That local authentication/session behavior is not being redesigned.

`app/Home.py` calls `require_authenticated` before repository creation/navigation. Every page calls `require_page_permission` or `require_operational_page` before business reads. `AuthorizedRepository` applies the existing permissions again to actions and receives the current app User as the audit/history actor. Report exports, including PDF, already use that actor through the existing logging paths. No new logging is needed.

The permission matrix below describes the unchanged initial page guard; operational New/Edit and write/export actions keep their additional existing checks. Admin-only controlled import/void actions remain as implemented. No role or permission set is changed.

| Page | Initial permission | Existing roles |
|---|---|---|
| `app/pages/10_Salmonella_Report.py` | `VIEW_REPORTS` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/11_Facilities.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/12_System_Status.py` | `VIEW_DIAGNOSTICS` | Admin, Developer |
| `app/pages/13_Facility_Details.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/14_Source_Data_Profiler.py` | `USE_PROFILER` | Admin, Developer |
| `app/pages/15_User_Management.py` | `MANAGE_USERS` | Admin |
| `app/pages/16_Audit_Log.py` | `VIEW_AUDIT` | Admin, Developer |
| `app/pages/17_Migration_Import.py` | `IMPORT_DATA` | Admin, Data Editor |
| `app/pages/18_Farm_Locations.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/19_Daily_Flock_Quota_Import.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/1_Production_Import.py` | `IMPORT_DATA` | Admin, Data Editor |
| `app/pages/20_EIMS_Reference_Data.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/21_Record_History.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/2_Production_Data.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/3_Accounts_Facilities_Flocks.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/4_Reports.py` | `VIEW_REPORTS` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/5_Flocks.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/6_Flock_Transactions.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/7_Quota_Registrations.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/8_Quota_Transactions.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |
| `app/pages/9_Salmonella_Tests.py` | `VIEW_DATA` | Admin, Data Editor, Reporting Viewer, Developer |

## Identity source and fail-safe plan

Use the supported viewer `st.user.user_name`, then the legacy `st.experimental_user.user_name` where available. Match normalized username, not email/LOGIN_NAME, to the new nullable APP_USER.SNOWFLAKE_USERNAME. The sole implicit role is the named main-admin constant EFNSDATABASE. Missing/ambiguous/inactive mappings deny before business navigation/reads. Missing mapping schema must not prevent the main account override.

Official sources: [Snowflake viewer identity](https://docs.snowflake.com/en/developer-guide/streamlit/app-development/personalization), [Streamlit 1.52 st.user](https://docs.streamlit.io/1.52.0/develop/api-reference/user/st.user). These identify st.user as platform-provided viewer information. Snowflake warns that CURRENT_USER may instead represent the app owner, so an unverified SQL result must never trigger the main-admin override. The fallback uses only an existing executor and fails closed when viewer scope cannot be established; no connection/session/right-mode change is made.

Implementation, schema review, assumptions, tests and shipped-file proof follow below. No Snowflake calls, operational DDL, deployment, PR or real-user/producer files are added by this task.

## Implementation and identity verification rule

The user explicitly approved fail-closed fallback: `app/snowflake_identity.py::resolve_snowflake_username` first reads `st.user.user_name`, then the older platform-supplied `st.experimental_user.user_name` if unavailable. These read-only viewer APIs are trusted because the authenticated Snowflake host supplies them. A malformed primary identity denies instead of selecting a different identity. Username is never read from a form, URL, email or a local login token.

Only when both APIs are unavailable may the resolver attempt `SELECT CURRENT_USER() AS USER_NAME` through an already-existing executor. It does not create or resolve a connection to do so. In this owner's-rights app there is no independent proof that an SQL identity is the viewer, so SQL-only identities are denied, including EFNSDATABASE or any mapped Admin. No caller-rights/session changes or verification-bypass flag are introduced. Missing identity in an active warehouse runtime no longer falls back to local password login. Explicit local development mode remains unchanged.

`MAIN_SNOWFLAKE_ADMIN_USERNAME='EFNSDATABASE'` is the sole implicit Admin. It applies only after a trusted viewer API identifies the exact canonical EFNSDATABASE principal. A quoted, case-distinct or space-padded lookalike does not receive the override. Ordinary User Management matches remain case-insensitive. [Snowflake identifier rules](https://docs.snowflake.com/en/sql-reference/identifiers-syntax) explain why the canonical principal check is needed. Its stable virtual app actor requires no APP_USER entry or new column, uses the existing Admin permission set, and is not an editable/deletable User Management row. No other username receives a default role. The reserved main name cannot be assigned to another app entry. Its actor label is EFNSDATABASE, rather than inventing an email address.

All other usernames match UPPER(TRIM(APP_USER.SNOWFLAKE_USERNAME)) with a bound value and LIMIT 2. Exactly one active entry is required; duplicates are denied even if only one is active. Invalid roles or absent/false ACTIVE are denied. ACTIVE is the app's existing enable/disable flag; disabling Snowflake sign-in itself remains the platform's responsibility and is not queried or changed.

Every denial uses the same message: "You do not have access to the EFNS app yet. Please contact the administrator." No username, mapping-existence, active state or raw SQL errors are shown. A hidden access-only navigation replaces previously rendered business navigation. No data repository reads or download controls are reached. Role updates are read afresh at existing guards, and the unchanged AuthorizedRepository binds the mapped User ID/email to its existing audit/history paths. No new sign-in logging or event types are added.

The sidebar shows the app name/role and Snowflake username. Only Admins see Sign-in diagnostics: trusted source, resolved username, matched entry (or main override) and schema availability. Unknown/denied users see no diagnostics. A general administrator-setup caption does not disclose whether their entry exists.

## User Management and schema review

The existing User model gains an optional snowflake_username. Existing admins can create, edit, clear and list it. No role/permission set changes. Values are trimmed and uppercased; blank means unmapped. The conservative supported format is an ordinary unquoted Snowflake username, up to 255 ASCII letters/digits/underscores/dollar signs, beginning with a letter or underscore. LOGIN_NAME/work email is not substituted. Quoted, Unicode and email-shaped usernames need an explicitly reviewed extension rather than guessing.

Snowflake mapping writes re-use the unchanged continuity transaction/global intake-lock implementation for uniqueness validation plus write/audit. Uniqueness covers inactive entries too, because standard Snowflake UNIQUE constraints are not enforced. Raw/manual duplicate data fails closed at lookup. Existing user-management audit actions remain unchanged. Local SQLite user metadata supports the optional field and an equivalent normalized unique index; local password, hashing, token/session and logout methods are unchanged. Isolated test databases exercise that local metadata upgrade; no operational database DDL is run.

Review only `sql/35_app_user_snowflake_username_20261120.sql` (also in the fresh-install definition `sql/05_security_tables.sql`):

```sql
ALTER TABLE EFNS_DEV.SECURITY.APP_USER
    ADD COLUMN IF NOT EXISTS SNOWFLAKE_USERNAME VARCHAR(255);
```

No grants, backfill, user/role creation or default mappings are added. Existing app-owner grants and lock row are reused. With the new column absent, the trusted main identity still resolves as Admin; other identities get the generic denial. User Management can show existing entries and role settings, but disables mapping fields and shows the schema-update note until the column is available. An empty user list still renders Add user safely.

## Scope and assumptions

- Existing local development password sign-in remains supported. Snowflake mode never uses a local token/email as an identity fallback.
- Existing emails, names, roles and activation rules stay as before; mapping is optional and intentionally not auto-populated from email.
- A reserved virtual main actor is stable across deployments and intentionally has no user-table row. Current and historical actor lookup supports that label.
- Current owner-context SQL cannot verify the viewer; SQL-only fallback remains denied until an independently verified platform mechanism is available. No connection/session change is part of this task.
- Previously granted app operations keep their exact permissions. The new mapping field is manageable only through the existing MANAGE_USERS guard.
- No report/calculation/import/quota rule, business table or existing stored business data changes.

## Protected-area files

| File | Narrow reason |
|---|---|
| `app/snowflake_identity.py` | New single trusted viewer resolver, normalized username validation and named main override. |
| `app/auth.py` | Map the trusted username, render uniform denial and Admin-only diagnostics; local login/session/permission guard methods unchanged. |
| `app/runtime.py` | An active warehouse without identity fails closed as Snowflake, never into local password mode. |
| `app/security.py` | Optional user metadata and local User Management persistence/uniqueness; permission sets, passwords and sessions unchanged. |
| `app/snowflake_security.py` | Username lookup and User Management field writes under the existing lock; no platform authentication or connection changes. |
| `app/pages/15_User_Management.py` | Admin-only field/list display and safe empty/old-schema states. |
| `sql/05_security_tables.sql`, `sql/35_app_user_snowflake_username_20261120.sql` | Review-only nullable mapping column; no DDL executed against Snowflake. |

Existing identity tests modified in `tests/test_snowflake_security.py`: runtime auto-detection now denies missing warehouse identity instead of using local login; the old email-identity fixture now maps USER_A; the CRUD SQL fake removes the obsolete extra email lookup. The test that asserts user-management permission enforcement and all existing permission tests remain unchanged. 172 focused tests passed, including all 21 page denial checks, metadata CRUD/races, audit/history actors, empty/missing schema, SQL-only denial, revocation, and local session behavior. Full suites and shipped-file proof follow below.

| Shipped file | Base SHA-256 | Final SHA-256 |
|---|---|---|
| `app/auth.py` | `9f7b9578cdf8d8bbda5c6bef795bbbc2cabe6ea21276b38b01288d177210d48e` | `fb082b377a6304a153a23d515bbfcde2f08ad0e97d03fe2ca9e3a0552a2ddc8c` |
| `app/pages/15_User_Management.py` | `c2cf52bd570483dd21740bf0701379742929f5b6c678fa0ebfbc438da1d9b869` | `3efa045959ba6f832bf1c80e45919c86f9610bc8930dc95128feb4a9c3940911` |
| `app/runtime.py` | `066a03769b20a1c152ae8bb85a3b5df0437ba6f5a02416031f936121a1806304` | `0f25eba1df401c48180c114ba6fa4006f74f86c0fbcb51f83184a3d16c72b176` |
| `app/security.py` | `e130c85e92307fce54553ca2b8a122a3dd021eefe2275791c3fa6b8e6669b045` | `2b4e5e7590537d69e048c552bc7246fc8477962477f105713d70acd9ca131732` |
| `app/snowflake_identity.py` | `NEW` | `2716a43bdc64f53288263e16b94851ff281521c9e8a9cbc77fa13afd16fd8d67` |
| `app/snowflake_security.py` | `56a8c290f21c1e6cb9cc4437f52b5fed6bf7beba67dc0f570d510100943f048e` | `345ffa489e27ed161693380d783999b595fa6dfe3d3cfde3cfcccd350e5ccfa7` |

6 shipped files changed/added; 122 other shipped files are byte-identical; none removed.

The first full release run passed 2,479 tests and skipped one, but its static file-navigation scan rejected the new access-denial no-op callable. `tests/test_snowflake_navigation.py` now validates that exact callable only in the denial renderer, with its exact title/default and hidden navigation. All original file-target/path-resolver assertions remain. No runtime change was made for this test correction. The full suite is rerun after the correction.

## Final file scope and validation

All changed files are inside releases/employee_trial_2026_10_29:

- app/auth.py
- app/runtime.py
- app/security.py
- app/snowflake_identity.py (new)
- app/snowflake_security.py
- app/pages/15_User_Management.py
- sql/05_security_tables.sql
- sql/35_app_user_snowflake_username_20261120.sql (new, review only)
- tests/test_snowflake_security.py
- tests/test_snowflake_navigation.py
- tests/test_snowflake_role_mapping.py (new, synthetic users only)
- docs/codex_reports/LOGIN_ROLE_MAPPING_20261120.md (new)
- DELIVERY_RUNTIME_DIFF_20261030.json

Source comparisons against the base confirm the exact existing Role/Permission definitions, permission sets/checks and local password/session methods are unchanged (14 protected definitions in security.py and seven in auth.py). data/connection.py, data/repositories/snowflake.py (including the existing lock/transaction implementation), and app/services/authorized_repository.py are unchanged. All report builders, business SQL, import and quota rules remain byte-identical. No real-data fixtures/exports were added.

Root suite: 706 passed, 0 failed, 0 errors. Identity/auth focused suite: 172 passed; navigation suite after the static callable correction: 19 passed. Final release-suite result is recorded below. Manifest: 162 LF-normalized candidate hashes, regenerated from the base entries plus this task's final paths.

Final full validation: release Python 3.12 suite **2,480 passed, 1 skipped, 0 failed, 0 errors** (23m05s); root Python 3.11 suite **706 passed, 0 failed, 0 errors**. The baseline was 2,334 passed/1 skipped in the release and 706 passed at root; the 146 added cases account for the release increase. Existing report-number and permission tests pass unchanged. The final documentation-only result update is followed by regenerated hashes and the integrity guards. No Snowflake calls, operational DDL, deployment or PR occurred.
