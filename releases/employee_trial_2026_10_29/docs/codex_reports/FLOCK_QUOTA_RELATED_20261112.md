# Flock linked Quota — 2026-11-12

Branch: `codex-flock-quota-related-20261112`; base `origin/main` at `c9249684a3f01c7bf16bb3202e012515e5bb1445`. Separate worktree: `.local/flock-quota-related-worktree`.

## Investigation and scope

- `app/pages/5_Flocks.py` already showed Account and Facility with registered-page buttons in Summary. Related Records contained child Flock Transactions, Salmonella Tests and matched production tables, not the parent Account/Facility entries. Those existing sections stay unchanged.
- Details already exposed the stored `QUOTA_ID` and `FLOCK_QUOTA_TYPE` through its generic field table. This change adds readable relationship fields and navigation; it does not modify that table or any saved relationship.
- The Quota Registration page title uses `QUOTA_NAME`, then `REGISTRATION_NUMBER`, then “Quota Registration” (`quota_title` in `app/pages/7_Quota_Registrations.py`). The new Flock view service follows that precedence with null-safe text handling.
- Existing `get_quota_registration(id)` is present in BaseRepository, MockRepository and SnowflakeRepository. It is called once per Flock detail render, only for the stored nonblank ID; both tabs reuse the result. No whole-registration-table lookup, new SQL, repository method, schema or dependency was added.
- Flocks and Quota Registrations both require `VIEW_DATA` through `require_operational_page`. The existing AuthorizedRepository also guards this read with `VIEW_DATA`. All four current roles have it. The new display checks that permission and suppresses the lookup/link when unavailable; a repository authorization denial displays a neutral note without exposing a new quota label.
- No list, create/edit, save, validation, initial-position, Delivery, calculation, import or report behavior changed. The Flock form/save block was compared against the base source and is unchanged. No protected repository/auth/connection file was edited.

Implementation points: `app/pages/5_Flocks.py:62` renders the shared rows; `:114` resolves the relationship once; `:126` and `:154` place it in Summary and Related Records. `app/services/flock_related.py:17` handles label/null/permission state, using the existing repository read at `:30`.

## New rows — screenshot-equivalent description

In **Summary**, below the existing Account/Facility controls, and at the start of **Related Records** in a bordered parent-record entry:

```text
Quota
Synthetic layer registration
Flock Quota Type
Egg Production
[View Quota Registration]
```

The button uses the same `open_module(..., "detail", id)` navigation as Account/Facility, targeting the already registered Quota Registrations page. Summary and Related Records use separate widget keys. The displayed type is the flock’s stored type, not a replacement inferred from the linked registration.

| Relationship state | Quota row | Small note | Button |
| --- | --- | --- | --- |
| Found, including an Inactive registration | Existing Quota page title/name fallback | None | View Quota Registration |
| No stored quota ID | — | None | None |
| Stale ID | Stored ID as text | Quota Registration not found. | None |
| Quota read not permitted | — | Quota details are not available for your role. | None |

Flock Quota Type remains a separate read-only field in each case; missing type displays “—”. No label is written back to the flock.

## Tests and data safeguards

Synthetic tests in `tests/test_flock_quota_related.py` exercise MockRepository and the actual SnowflakeRepository read implementation with an injected read-only executor double. The double verifies a scoped, bound `QUOTA_ID` read and rejects writes; it never creates a Snowflake connection. UI tests cover both tabs, all current roles, missing/stale/NULL values, authorization denial, both buttons and both application entrypoints. Frame comparisons verify that rendering and navigation leave record data unchanged.

- Focused new/existing navigation and date-default coverage: **54 passed**.
- Before change, full release suite: **1,980 passed, 1 skipped, 0 failed, 0 errors** (539.04 s).
- Before change, full root suite: **706 passed, 0 skipped, 0 failed, 0 errors** (140.86 s).
- After change, full release suite: **2,012 passed, 1 skipped, 0 failed, 0 errors** (516.54 s).
- After change, full root suite: **706 passed, 0 skipped, 0 failed, 0 errors** (118.59 s).
- The release increase is exactly **32 new synthetic test cases**. Existing tests and expectations are unchanged.

| Suite | Before passed / skipped / failed / errors | After passed / skipped / failed / errors |
| --- | --- | --- |
| Release | 1,980 / 1 / 0 / 0 | 2,012 / 1 / 0 / 0 |
| Root | 706 / 0 / 0 / 0 | 706 / 0 / 0 / 0 |

Both full runs used `python -m pytest -q` from their respective directories, with the existing release environment and root Python 3.11 CI environment. Final documentation/manifest updates were followed by the integrity guard and an independent check of every candidate hash.

No real producer/flock exports or fixture files were added. No live `flockdev-23` record was inspected. Tests use synthetic in-memory records only. No Snowflake access, deployment or PR.

## Shipped-file hash proof

Raw SHA-256 was captured before code changes for every source matched by `snowflake.yml` artifacts, plus the root entrypoint, environment and theme config. Only the following shipped files change:

| Shipped file | Before raw SHA-256 | After raw SHA-256 |
| --- | --- | --- |
| `app/pages/5_Flocks.py` | `d0931c039d4838d43c66f629759327666a52d291d9190dc4a0f9838ca18692aa` | `657a5efbea6eb890e319cd09bc10e25efc0d6b5460be54c9d9af5e756f58abcd` |
| `app/services/flock_related.py` | — (new file) | `a054e55b55f2216c3d6c0b2f60264138f0350d56f7a4bc354d38a24934b571e6` |

Artifact counts: **113 before, 114 after**: one modified page, one new view service, zero removed files. All **112 other shipped files remain byte-identical**, including every existing service, repository, config, asset and entrypoint. The new service is included by the existing `app/services/*.py` artifact pattern; `snowflake.yml` is unchanged.

Unchanged-set digest (sorted release-relative `path + NUL + raw SHA-256 + newline`, UTF-8): `1b8c46813a1e16d23e777073b3bf9802583d585be3fa50fd51b49f6617ef0274` before and after. The verification checks the exact matched path sets and every raw file hash, not only this aggregate.

The live runtime-diff manifest is regenerated from LF-normalized final bytes, starting from main’s version and preserving every existing entry. It contains **91 candidate hashes** including the new service, tests and this report. Historical captured-source and patch manifests remain baseline evidence; no hand-merging or rewriting of their captured hashes occurs.

## Follow-up only

The Quota Registration page already has a reverse Flocks related table filtered by `QUOTA_ID`. No reverse-link behavior was changed. Any further review or enhancement of that reverse section is a separate follow-up. Quota editing from the Flock view is out of scope.
