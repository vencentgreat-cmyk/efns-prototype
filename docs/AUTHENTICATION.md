# Prototype Authentication and Authorization

EFNS uses one `AuthStore` contract with two runtime backends.

- **Local:** SQLite at `.local/efns_auth.db`, salted PBKDF2-SHA256 hashes,
  revocable eight-hour sessions, and the four prototype accounts.
- **Streamlit in Snowflake:** trusted viewer identity from `st.user.email`, with
  roles and active status in `EFNS_DEV.SECURITY.APP_USER` and audit events in
  `EFNS_DEV.APP.AUDIT_EVENT`. No application password form or password hash is
  created in this mode.

Only normalized email addresses ending exactly in `@nsegg.ca` can authenticate
or be created. Sessions use random server-side tokens, expire after eight hours,
and stop resolving when a user is deleted or deactivated.

## Roles

| Capability | Admin | Data Editor | Reporting Viewer | Developer |
|---|---:|---:|---:|---:|
| View operational data | Yes | Yes | Yes | Yes |
| View reports | Yes | Yes | Yes | Yes |
| Import data | Yes | Yes | No | No |
| Create/update operational data | Yes | Yes | No | No |
| Delete operational data | Yes | No | No | No |
| Source profiler and diagnostics | Yes | No | No | Yes |
| Audit log | Yes | No | No | Yes |
| User administration | Yes | No | No | No |

Navigation is filtered for usability. Security is also enforced by direct page
guards, Admin-only user-store methods, and an authorized repository proxy that
checks writes before calling Mock or Snowflake repositories.

Four prototype accounts are seeded on first use:

- `prototype.admin@nsegg.ca`
- `prototype.editor@nsegg.ca`
- `prototype.reporter@nsegg.ca`
- `prototype.developer@nsegg.ca`

Their initial passwords are distributed separately and must be changed at first
login. Admin-created and reset temporary passwords are shown once in the active
browser session.

## Runtime selection

`EFNS_RUNTIME_MODE=local` is recommended for local development. `auto` selects
Snowflake only when Streamlit exposes both a viewer email and an active warehouse
session; the deployed app uses this default. `REPOSITORY_MODE` can still explicitly select `mock` or `snowflake`; if
it is omitted, Snowflake viewer mode defaults the repository to Snowflake.

The email must end exactly in `@nsegg.ca`, and a matching active row must exist
in `SECURITY.APP_USER`. The table role remains the authority for application
permissions. Snowflake account roles only control whether a viewer can open the
Streamlit object.

## Remaining production controls

Snowflake authentication and MFA policy remain account responsibilities. Before
production, define joiner/mover/leaver procedures, audit retention, emergency
access, monitoring, and periodic access reviews. The local SQLite backend remains
prototype-only and is never included in the Snowflake deployment artifact list.
