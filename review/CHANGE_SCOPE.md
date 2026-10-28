# Change scope and provenance

The frozen zero-count application is the only runtime baseline. This directory
does not incorporate later root-worktree changes or old date-repair modules.
The deployment descriptor, environment.yml, theme and mapping configs are
retained. The only application-byte exception is four disabled prototype
password-hash constants, documented in SHARING_AUDIT; it is not a deployable fix.

## Prior business-acceptance candidate delta from its saved live baseline

| File(s) | Candidate intent |
|---|---|
| `data/flock_quantity.py` (new) | Explicit current Count/Removal with request identity, revision/audit, CAS and rollback |
| `app/services/quota_usage.py` (new) | Shared Account Bird Count aggregation, Facility/unassigned breakdown, missing/type caveats and no invented quota baseline |
| `data/validation.py` | Finite/typed daily values and relationships; current Count0 exception, not blanket historical policy changes |
| `data/repositories/base.py`, `continuity.py`, `mock.py`, `snowflake.py` | Consistent current-quantity API, persisted history and repository validation/guards |
| `app/services/authorized_repository.py` | Authenticated actor and required create/update permissions on quantity apply |
| `app/pages/6_Flock_Transactions.py` | Ordinary activity versus explicitly confirmed current apply;0 input and reason |
| `app/pages/3_Accounts_Facilities_Flocks.py`, `5_Flocks.py`, `7_Quota_Registrations.py` | Same Account-wide aggregate shown with scope and unavailable baseline |
| `app/pages/11_Facilities.py`, `9_Salmonella_Tests.py` | Related local workflow/date handling fixes tested in staff acceptance |
| `app/ui.py` | Missing optional form dates remain missing |
| `app/navigation.py` | Save-button permission handling; routing helpers unchanged |

14 modified and2 new runtime files versus that saved live baseline. This table
describes candidate intent, not proof that every behavior is correct/deployed.
Read the actual implementations and failure witnesses.

## Zero-count revision within that candidate

Only `data/validation.py`, `data/flock_quantity.py` and page6 changed from the
previous business candidate: finite non-negative confirmed Count including0,
canonical integer request payload, and input/default/help text that preserves0.
Other transaction types were not relaxed. No physical schema change is claimed
by this candidate. Existing SQL bootstrap drift is recorded separately.

## Kept from frozen live baseline

Date batch CAS/receipt handling, R1 and original mappings, strict company guards,
historical manual correction and transaction supplement, navigation, original
file trace, report count/NULL/export/provenance behavior and light theme remain
in this review. Hash comparisons prove preservation relative to the frozen
candidate; current company live status is not queried here.

## Added solely for independent review

README/REVIEW_GUIDE, exact share manifest and consistency/audit notes; a pinned
dependency closure; pytest/network/local storage configuration; copied
synthetic tests/helper packages and two offline scripts; checked static SQL
sources; an optional local reviewer creator; prepared GitHub Actions workflow;
and one strict expected-failure witness for a Mock timestamp collision.

Three copied test files have adaptations described in SHARING_AUDIT: named
AppTest entry, current theme assertion, deterministic stale token setup. Their
source/copy hashes and exception status are preserved in SOURCE_ORIGINS.
No review-only patch is applied back to the deployment candidate or original
Git worktree. No test fixture is copied from a real export.
