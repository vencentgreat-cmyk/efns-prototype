# Flock Status as-of fixes — 2026-11-13

Branch `codex-flock-status-asof-20261112`; base latest fetched main `2c75cf9ea93ec919448571a39fdada3e8c5fda35`, including Production PDF and Facility Housing. Requested rebase completed with “up to date”; the earlier checkpoint already descends from this main. No history was rewritten, so use a normal push. This report supersedes the preliminary 2026-11-12 investigation checkpoint. No Snowflake calls, SQL/repository edits, data changes, deployment or PR creation.

## Confirmed root cause and fix 1

User-provided read-only results establish that flock 40378 has two Counts on **2026-06-12**, both **39,552**, with Source Producer versus blank. The old shared builder treated source-label differences as a conflict. The earlier suspicion of missing June observations is superseded by this evidence: **this is a logic defect, not a need to add a Delivery for 40378**.

`app/services/flock_current_report.py` now resolves the latest date on/before the report date, still preferring Count over Delivery on a same-day tie. Every candidate must have a usable non-negative whole quantity; invalid quantities remain flagged and cannot be replaced by BIRD_COUNT. Equal usable quantities are accepted regardless of source. Different usable quantities still conflict. The selected metadata prefers a nonblank source; source does not decide quantity. Existing Flock Status/Current columns contain no source column, so no new output column is introduced; the selected row's source preference is tested directly.

For 40378 at 2026-06-19 and 0.4% mortality, the confirmed 39,552 Count seven days earlier yields **39,515 Inventory**. Tests cover blank/whitespace/different sources, both row orders, invalid quantities and same-date Count/Delivery preference.

## Fix 2 — upcoming flocks without an as-of observation

For an otherwise in-scope flock with Placement Date after the report date and **no** Count/Delivery on/before it: Inventory is **0** and Up. Flocks uses the validated stored **BIRD_COUNT**. Hatch Date is not an inclusion filter. Counted/Count Date remain blank because BIRD_COUNT is not a dated observation. Notes identify the fallback. With a known positive quota, Util. is **0.00%**; unknown/zero quota still follows the existing unavailable-percentage rule.

An earlier usable observation retains its existing priority, even when BIRD_COUNT differs. The fallback is not used for a placed flock, a missing placement, or an existing invalid/conflicting eligible observation. Invalid stored BIRD_COUNT leaves Up. Flocks unknown with a note, while future Inventory remains 0. Account and quota subtotals sum the displayed upcoming quantities, and notes disclose that they include the stored-count fallback while Counted remains unavailable.

These two calculation changes are in the shared Current builder, so its Age/Status/by Producer and other callers inherit them. No mortality, disposal, flock inclusion, quota-position or transaction-state rule was changed.

### Confirmed fallback contributions on 2026-06-19

Quantities are from the user's confirmed legacy comparison. Account registration mapping is supported by the existing committed DEV_FlockCurrent projection. Fixture dates used to test no-observation/hatch boundaries are synthetic; no new real-data exports were added.

| Producer registration | Flocks | Up. Flocks fallback contribution |
|---|---|---:|
| 7050 | 40397 | 15,674 |
| 7078 | 40404 | 28,800 |
| 7101 | 40399 | 51,300 |
| 7107 | 40396 | 39,772 |
| 7113 | 40406 | 10,700 |
| 7168 | 40405 | 36,000 |
| 7172 | 40400 + 40401 | 61,272 (35,568 + 25,704) |
| 7173 | 40403 | 80,640 |
| 7178 | 40398 | 24,712 |
| Total | Ten flocks | **348,870** |

These are the fallback contributions, not invented complete producer/grand upcoming totals: add each producer's already-qualifying observation-backed upcoming flocks, such as 40382, unchanged.

## Confirmed test-account exclusion

There is no dedicated IS_TEST_ACCOUNT field in the Account model. An existing DEV_TEST prefix convention elsewhere does not match `pr.12345regis`; DEFAULT_ON_REPORTS is not a dedicated test marker and is not repurposed. The smallest safe rule is an explicit exact-registration exclusion, trimming/case-folding **pr.12345regis**, in Flock Status, Flock Status by Producer and Producers Over Quota, as confirmed by the user. It excludes that Account's child flocks (including pr-11.13demotest and flockdev-23) and its quota contribution before rows, Inventory, allocation/issuance and producer counts are built. It does not match broad pr-* registrations, names containing “test”, or flock names alone. No data is deleted or edited.

The user explicitly confirmed the same exclusion for Producers Over Quota. Both builders use `without_confirmed_test_account` before rows and summary. The Producers Over Quota regression compares the complete real-producer result (including row metadata/highlights and all summary figures) before/after adding the test Account to the input; real producers remain unchanged.

## June legacy expectations and remaining data limits

Acceptance targets supplied by the user: province Inventory **979,290**; producer 7169 Inventory **87,743**, Util. **120.50%**. The confirmed duplicate source fix restores 40378 to 39,515; future fallback rows contribute 0 Inventory. The percentage arithmetic 87,743 / 72,816 rounds to 120.50% (72,816 is an explicit unit-test denominator, not a fresh verification of live quota sources).

A full June source transaction set/legacy screenshot has not been supplied in this task, and no database queries were run. Therefore **979,290 and 87,743 are acceptance targets, not claimed full-data reproductions**. No balancing flock quantity or remaining Inventory was fabricated to force those totals. Tests reproduce the confirmed 40378 result and all ten fallbacks; they separately verify the supplied percentage formatting.

Known gap: **40407 / producer 7038** is absent from the data, per the user. Its future-placement Inventory would be 0, so its absence alone does not lower province Inventory; it leaves the 7038 Up. Flocks contribution short by **11,000** and omits that detail row. This requires a separately authorized source/data import, not a fake report row. No row was created.

### Issue 3 — producer 7128 quota / effort to include

The existing quota loader `4_Reports.py::load_flock_report_quotas` calls `flock_age_report.py::build_flock_age_quotas`, which computes confirmed as-of positions only for owning Accounts with Active Egg Production registrations. Status detail/Account Total rows are built from eligible flock groups, whereas the province allocation quota map can include an Account with no eligible flock rows. This distinction must be checked before labelling 7128 a missing-quota calculation defect. Also distinguish a missing Account Total row from the Producers with Quota counter: the latter checks the Account PRODUCER_ROLE flag as well as positive quota, without changing the quota calculation itself.

| Evidence / cause | Smallest safe next step | Effort |
|---|---|---|
| 7128's quota is already in the map, but it has no eligible flocks and therefore no Account Total row | An approved quota-only Account Total row could be added in a separate report change, with zero Inventory and verified quota; no new SQL is needed if source inputs already exist. Decide whether to show only positive-quota Accounts so current zero-quota accounts are not unexpectedly added. | Small–medium, builder plus scope/export tests |
| Active registration and dated transactions exist, but the amount appears wrong | Inspect the registration, owner IDs, transaction dates, latest Base and RAW Active/Inactive evidence; use the existing confirmed rule. The committed quota-transaction fixture has a 45,495 Sale on 2026-07-08, which must not be subtracted in a June 19 report. November's 0 figure does not establish June's quota. | Small investigation; fix depends on evidence |
| Registration/transactions or RAW state evidence are missing, or registration is currently Inactive | Supply/repair verified source evidence through a separately approved data process. Do not invent quota or bypass the confirmed Active-registration rule. | Data work, not this report fallback |
| Business needs historical registration status instead of the current Active-registration scope | Requires an agreed historical-state rule and evidence; simply including every Inactive registration would change validated quota behavior. | Larger separate rules/history task |

No 7128 value or quota-only row was inserted by this task. The exact live cause remains unverified without its source records.

## Tests and current-date comparison

Final focused calculation/report run: **116 passed** (29.97s), including the full current-date frame and real-producer Producers Over Quota comparisons. The earlier focused run had 98 passes and one stale-manifest failure before regeneration; that integrity check now passes. Final full release suite: **2,111 passed, 1 skipped, 0 failed/errors** (1299.98s), Python 3.12.14, `python -m pytest -q --basetemp ../../.local/asof-release-temp` from the release. Final full root suite after the approved Producers Over Quota scope change: **706 passed, 0 skipped, 0 failed/errors** (210.25s), isolated Python 3.11, `python -m pytest -q --basetemp .local/asof-final-root-temp` from root. An earlier root run also passed 706 tests. Main baseline was 2,071 passed / 1 skipped; 41 new as-of cases were added and one obsolete source-conflict parametrization was replaced by the new source-agnostic regressions.

The 2026-11-13 normal observation-backed Status fixture is frozen against main, including a SHA-256 over **every displayed cell/column**, core row quantities/ages/percentages and the entire summary. It is unchanged. Existing current legacy fixtures also remain regression coverage. This does not claim all live current-date data is unchanged: equal-quantity source conflicts, missing-observation future rows and the explicitly excluded test Account intentionally change wherever present.

## Shipped byte proof

All snowflake.yml artifact globs plus streamlit_app.py, environment.yml and .streamlit/config.toml were raw-SHA-256 snapshotted before edits. Before/after shipped file count: **116**. Changed shipped paths:

| Shipped path | Before raw SHA-256 | After raw SHA-256 |
|---|---|---|
| `app/services/flock_current_report.py` | `be6d68d90a61d0eaebc6ef29597fa2c3a2dae6daa545bdc3f44eebad2e8dc4e8` | `694e7e6642dceeea4988806102f64052c269c42680d84c076aba3dc63423c6a8` |
| `app/services/flock_reports.py` | `b297542a7e46bd652e84b2d61b3c0638e3f97c21f6222d4d43aef99bc56c8b96` | `3958ac0856070fe82099a2c39b34c9f26a8ade4eba0556352dcf798e334c1dfa` |
| `app/services/producers_over_quota_report.py` | `f006f59d204ec40e11a69a5bdf73786c61ede820ff7e3c551abd3dc53783a607` | `cd1b18832dbb19f57818b6d34b7774891f28ce5d307c7497ab7a442af27513c5` |

**113 other shipped files are byte-identical.** No repository, SQL, schema, authentication, write, connection or lock file changed. No real data files were added. The live runtime-diff manifest starts from main and is regenerated over all final LF-normalized bytes; independently verified candidate hash count is **101**. Historical captured-source manifests are unchanged.
