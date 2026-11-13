# Flock Status observation conflict rule — 2026-11-13

Branch: `codex-flock-status-conflict-rule-20261113`; isolated worktree `.local/flock-status-conflict-rule-worktree`. Base: latest fetched main **695a8b8cb21c135ff4ea5a0f4cc9d648ea1b2228** (PR #29), verified to contain the merged as-of fix 776784f. No other branch/worktree modified. No deployment, PR creation, Snowflake calls, data changes, new SQL or repository change.

## Confirmed example and result

User-provided legacy evidence: permit **40357**, producer **7159**, Count date **2026-07-10**:

| Quantity | Count source | Updated At |
|---:|---|---|
| 39,440 | blank | 2026-10-21 |
| 38,866 | Producer | 2026-10-30 |

The old rule returned unknown because the quantities differed. The new first preference selects the unique sourced quantity **38,866**. At **2026-07-31**, mortality **0.4% per month**, the unchanged exact-arithmetic mortality formula gives **38,758 Inventory**, matching the supplied legacy value. Fixture placement/hatch dates are explicitly synthetic past dates, since the user did not supply them; they assert the placed case without inventing source parity for those fields.

## Exact selection policy

`app/services/flock_current_report.py::latest_observation` preserves the latest eligible business date and same-date Count-over-Delivery priority. Only after those filters:

1. Any NULL, negative, fractional or otherwise unusable candidate quantity remains invalid and unknown, preserving the prior invalid-quantity rule. No sourced/newer row hides an invalid quantity.
2. If all usable quantities agree, accept that quantity regardless of source/time, as before. Prefer nonblank source metadata; no tie-break note is added because no quantity decision was needed.
3. With different quantities, if nonblank-source candidates contain exactly one **distinct** usable quantity, use it. Several sourced rows agreeing on that quantity qualify. This preference wins even if a blank-source row was updated later.
4. Otherwise compare UPDATED_AT across the candidate rows, normalized to UTC. Use the newest timestamp only if its rows agree on quantity; prefer nonblank metadata among those agreeing newest rows. This fallback may select a blank-source row if it is uniquely newest. Do not substitute CREATED_AT.
5. If timestamp ordering is unavailable/invalid, or newest timestamp rows disagree, retain the conflict and “—”. This includes tied blank-source rows as well as the user's tied, differently sourced example; no arbitrary row order decides quantity.

UPDATED_AT is ordering metadata, not the observation's business date. It is not restricted to the report's As of Date: the supplied July example intentionally uses October updates to select the currently corrected July Count. Hatch/placement/disposal eligibility, mortality, quotas, current transaction-state rules, future-date filtering and the ten upcoming BIRD_COUNT fallbacks remain unchanged. No stored Count/Delivery is edited, deduplicated or deleted.

## Visible note

For the confirmed example the report shows:

> 7159, permit 40357: 2 Counts on 2026-07-10 with different quantities; the sourced record was used

The timestamp fallback instead says “the most recently updated record was used”. Every successful quantity tie-break produces a note. Unresolved conflicts retain their Count/Delivery conflict note and now also carry its producer/permit context through the same visible-note path. Missing registration numbers fall back to the Account name, without adding a raw internal ID to the note.

The Current builder retains the row Notes text and supplies contextual `result.attrs['notes']`; Flock Age carries it forward. Flock Status/by Producer preserve the notes and append them to the existing summary Notes caption, so no Reports page or column change is required. Existing PDF footnote collection recognizes the same attrs. The selected-producer view shows its own contextual notes, not other producers' conflict details. Producers Over Quota already builds contextual row notes from the shared Current result; its calculation logic and source file do not change here.

## Scope and validation

Initial focused run: **134 passed**, one expected stale-manifest integrity failure before regeneration. The new visible-note AppTests passed in that run. A test-only pandas dtype warning was removed by explicitly making its deliberately invalid-quantity fixture column object-typed; no warning was suppressed.

Final focused run: **136 passed, 0 failed/errors** (18.12s), covering all listed report tests including the merged as-of regressions. Full root suite: **706 passed, 0 skipped, 0 failed/errors** (152.77s), isolated Python 3.11, `python -m pytest -q --basetemp .local/conflict-root-temp` from root. Full release suite: **2,131 passed, 1 skipped, 0 failed/errors** (547.20s), Python 3.12.14, `python -m pytest -q --basetemp ../../.local/conflict-release-temp` from the release directory. Main baseline was 2,111 passed / 1 skipped; this branch adds 20 passing cases. The unchanged as-of tests and frozen current-date report passed in both focused and full runs. Tests cover: the confirmed 40357 result and both input orders; sourced preference with a newer blank row; multiple sourced rows sharing one distinct quantity; blank-source timestamp fallback; multiple sourced quantities followed by timestamp fallback; tied newest timestamps; UTC-equivalent timestamps; missing/bad ordering evidence; invalid quantities; equal quantities without extra notes; latest business-date and Count/Delivery precedence; visible captions in both Status pages; readable notes without registration numbers.

The merged as-of test file is retained, including 40378, all ten BIRD_COUNT fallbacks, no Hatch Date exclusion, the exact test-account filter in both Status and Producers Over Quota, real-producer invariance, and the frozen full current-date frame/summary. One existing conflict fixture's second source is changed from blank to Board: the new rule deliberately resolves a sourced-versus-blank quantity disagreement, so the unresolved-conflict regression now uses two sourced quantities without timestamp evidence. Its assertion remains “—”/Count conflict. No test was deleted, skipped or relaxed to accept a wrong quantity.

This fixes the supplied observation choice; it does not claim a fresh database-wide or whole legacy-report reconciliation. No source evidence was queried directly and no live records were manufactured. Issue 3 / 7128 and the absent 40407 data remain outside this follow-up.

## Shipped-file byte identity

Raw SHA-256 was captured before edits for every snowflake.yml artifact plus streamlit_app.py, environment.yml and .streamlit/config.toml. **116 files before and after**; only these shipped files changed:

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/services/flock_age_report.py` | `542aba673bacfc56cb75fee4625b04191f57b48538693ef3bf6f81c84caa2453` | `799bae51f396f17cda5f0ccd0ed4e46b598e00e549c276a1ee49f74f779f3a3a` |
| `app/services/flock_current_report.py` | `694e7e6642dceeea4988806102f64052c269c42680d84c076aba3dc63423c6a8` | `17f6f623eea00b15212056c5a711f86aa9bf04f908b943daf495bd731bd34404` |
| `app/services/flock_reports.py` | `3958ac0856070fe82099a2c39b34c9f26a8ade4eba0556352dcf798e334c1dfa` | `1fefc5608862f13e1433a7416a64c3e925587b6f896e7f3a674b82f890c86f87` |

**113 other shipped files are byte-identical**, including the Reports page, PDF framework, repositories, schema/config, authentication and all write/lock/connection paths. No new real-data file or dependency is added.

Other changes are the new synthetic test/report, the one conflict-fixture source label in the existing as-of tests, and DELIVERY_RUNTIME_DIFF_20261030.json. The live manifest starts from main and is regenerated over final LF-normalized bytes, preserving all main entries and adding two paths, for **103 candidate hashes**. No manifest conflict or hand-merging occurred. Historical captured-source manifests remain unchanged.
