# Flock date defaults — 2026-11-11

Branch: `codex-flock-date-defaults-20261111`.
Base: `origin/main` at `34122e7d43bd0ed43285cc9671f08b0903df0af5`, including
PR #20 (Sara feedback) and PR #21 (Producers Over Quota parity).
Worktree: `.local/flock-date-defaults-worktree`.

## Behavior

- New Flock only: Placement defaults to Hatch + 133 days (19 weeks).
  Estimated Disposal defaults to Placement + 364 days (52 weeks).
- Each generated value follows its upstream date until that field is manually
  edited. An override survives upstream changes and unrelated reruns. Clearing
  the field re-enables its default immediately if the upstream date is present.
  An Estimated Disposal override is independent of a Placement override.
- If the upstream date is empty, its automatic dependent default is empty.
  Explicit overrides remain intact. Existing required-field validation still
  applies on save.
- Edit mode never applies defaults, including to stored blank values. Comparison
  captions show the calculated dates only where they differ from stored dates;
  captions use the current Hatch/Placement input without changing stored dates.
- Caption: “Placement = Hatch + 19 weeks; Estimated Disposal = Placement + 52 weeks
  (defaults, can be changed)”.

The constants live only in `app/services/flock_date_defaults.py`. Source: the
user's legacy analysis of 2,172 Active flocks; 238/247 recent placements matched
19 weeks and 230/247 estimated disposals matched 52 weeks. Staff confirmation is
pending. These observations supply editable defaults, not new validation rules.
No real-data exports or fixtures were added.

## Scope and verification

Only `app/pages/5_Flocks.py` consumes the new pure helper. Existing save,
validation, quota, initial-position and Delivery code paths are unchanged. No
report, SQL, repository, other page, or stored data was changed. The existing
`app/services/*.py` deployment artifact pattern includes the new helper.

Synthetic tests cover leap years, month ends, empty dates, manual overrides,
clear-to-reset, Streamlit reruns, edit preservation (including blank stored
dates), comparison captions, create/save defaults, the unselected initial
position/Delivery controls, and explicit initial-position/Delivery selection.
The existing initial-position regressions also run in the full suite.
The existing occupied-facility form test now expects the new create defaults;
it still verifies Actual Disposal remains blank and all existing flocks remain
unchanged.

Validation commands (run from the corresponding worktree directories):

```powershell
# Release directory, existing release virtual environment
python -m pytest -q
# Repository root, existing Python 3.11 CI environment with lxml
python -m pytest -q
```

Results:

- Full release suite: **1,980 passed, 1 skipped, 0 failed, 0 errors** (694.97 s).
- Full root suite: **706 passed, 0 skipped, 0 failed, 0 errors** (221.37 s).
- Focused defaults, occupied-facility and integrity checks: **24 passed**.
- Manifest: **88 verified hashes**, regenerated from LF-normalized final file
  bytes, including this report and both changed test files.

No Snowflake connection, deployment, PR, or modification of another worktree.
