# Facility/Flock design review

Reviewed 9 October 2026. Business evidence: Sara's meeting on 8 October 2026,
reported by the user. Physical evidence: read-only EFNS_DEV metadata and original
migration RAW; no database, original source or committed batch was changed.

## Confirmed model

One Facility can accommodate different Flocks over time and concurrent Flocks.
There is no confirmed maximum. A Flock still has only one nullable Facility FK;
there is no evidence for a multi-Facility Flock or a need for a junction table.
The editable Crow's Foot source is [facility_flock_erd.mmd](facility_flock_erd.mmd).
`|o` on the Facility end means zero or one Facility for each Flock; `o{` on the
Flock end means zero or many Flocks for each Facility.

The diagram represents deployed FK declarations. Account equality is a separate
application/migration rule, not a composite FK. PK/FK enforcement on these
standard Snowflake tables must not be equated with application validation.

## Inspection results

| Surface | Finding / change |
| --- | --- |
| DEV metadata | FLOCK.FACILITY_ID nullable; SHOW UNIQUE KEYS returned no rows; FK_FLOCK_FACILITY references CORE.FACILITY.FACILITY_ID |
| SQL setup/additive deployment | No Facility uniqueness or occupancy upper bound; no DDL required |
| Flock form / repository | Lists all facilities of selected Account, including occupied ones; inserts by FLOCK_ID; retains prior Flocks |
| Facility details page | Related Flocks uses get_flocks(facility_id), returning all matches |
| Validation / operational imports | No overlap or single-active-Flock restriction; Account ownership and within-record date ordering checks remain |
| Historical migration / corrections | Preserves GUIDs, date values and Facility links; Account conflicts remain pending |
| Custom Report Center | Flock dataset now exposes placement, actual disposal and forecast separately; one record per FLOCK_ID before grouping |
| Older joined report builder | Forecast and actual disposal separate; Facility lookup uses FACILITY_ID; Flock/Facility/Producer Accounts are separate, with many-to-one parent checks |
| Reporting SQL | Prepared view update exposes both Account roles on VW_FLOCK_DETAIL and uses LEFT JOIN to Import Batch in production views; local SQL is not yet deployed |

Placement/disposal fields can show known dates but do not provide complete
occupancy history when unknown or when disposal is partial. Do not substitute
estimated disposal, classify null disposal as definitely current, or reject
overlap. Reporting sums of Bird Count are record totals, not verified live stock.

## Migration impact

Original batch DEV_MIGRATION_255ef9b50a52e766a7dff9 remains COMMITTED.
First correction remains COMMITTED_WITH_PENDING: 112 committed, 159 pending.
The current read-only repository preview independently returns 112 already
committed, zero newly ready, and 159 pending; it does not count the 112 again.
Six Flocks have a different Account from their one shared Facility; 57 dependent
transactions stay pending. Sharing confirmation does not resolve these 63 rows.
Other pending groups are 28 missing Flock links, 38 missing Quota links and 30
dependent Quota transactions. No newly eligible correction rows are authorized.

The earlier source audit found 95 shared Facility GUIDs / 657 Flock GUIDs,
651 same-Account and six conflicting references; zero RAW-to-normalized Facility
rewrites. Rejected normalized rows are null, so a NORMALIZED_DATA-only count
reports 651, not the full source 657. This is not a mapping-created conflict.

## Business questions (no automatic correction)

For the six Flocks at Facility 99F5D673-E81D-E611-80E5-C4346BAC339C,
confirm which source reference is correct, or supply evidence of authorized
cross-Account use / historical ownership and its effective dates. Names and
source-row evidence are supplied in a local review note, not copied into Git.
The Flock Account GUID is CC48413D-CDE6-E511-80E1-C4346BAC339C; the Facility
Account GUID is D148413D-CDE6-E511-80E1-C4346BAC339C. Similar names are not
proof of identical ownership. RAW shows the mismatch already existed at source.

Also confirm whether disposal date means full vacancy or a partial disposal,
and what evidence should support historical/current occupancy queries.

## Deployment boundary

This change updates local report code, documentation and synthetic tests only.
No schema change, migration re-run, pending-row write, deployment or commit is
performed. Existing DEV cardinality is already compatible with Sara's rule.
