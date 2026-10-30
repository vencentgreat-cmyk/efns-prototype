# Quota and current flock scope — confirmation sheet

Status: **PENDING. No approved position or utilization formula.** Date: 29 October 2026.

The supplied aggregate CSVs were read locally, not rerun against Snowflake. RAW
describes one original batch; later supplemental sources and current CORE can
differ. Counts below do not prove a balance, lifecycle, or complete reporting.

| Confirmation needed | Evidence / proposed question | Answer |
|---|---|---|
| Account entitlement and units | Confirm type/unit, authoritative starting position and date. Proposed signs: Base +, Adjustment signed, Global Adjustment +, Purchase +, Sale −. Are Base records observations or cumulative opening entries that must not all be added? | ______ |
| Leases and termination | Proposed inclusive lease dates: Effective Date ≤ as-of ≤ End Date. Confirm expiry, linked transaction handling and Terminate Quota (two zero-valued rows). A transfer has one owner-side entry per party; Related Account must not be counted as Owner. | ______ |
| Allocation / adjustment meaning | National Allocation (1) and Provincial Allocation (16) are outside Account entitlement and will not be imported into QUOTA_TRANSACTION. What province/national series do they represent? Does Global Adjustment relate to that series or QUOTA_ALLOCATION? Its type alone does not establish scope. | ______ |
| Initial flag and reserve | Yes/No split cohorts, not signs. Yes has empty reserve/NULL credit and linked pairs; No has reserve 0/Non One Time Credit. Does Yes mean legacy initial load and No later Dataverse creation? Zero/empty reserve is not capacity. | ______ |
| Trusted old count / counter priority | Was NEW_NETBIRDCOUNT the number staff relied on? It is an old-system reference, not an approved formula. What priority applies to Producer/Board/EFC/CEMA observations? Same-day different-source Counts remain conflicts, never auto-picked. | ______ |
| Live flock and end | Does EFC_PERMITACTIVE=Yes mean currently housed? How should No/unknown and actual disposal affect a dated live scope? Record Active/Inactive is not lifecycle. Delivery−Removal−Sale alone overstates many ended flocks. No automatic clearing/end event is introduced. | ______ |
| Inactive transactions | Are the 13 quota and 35 flock Inactive RAW transactions voided? Until clarified they are excluded from candidate calculations and block a certified result. CORE transaction tables do not retain this record state. | ______ |
| Missing-source attribution | Resolve owner Registration GUIDs for non-allocation RAW rows missing from CORE. Unknown Owner is not a counterparty or a name-derived guess. Missing rows block that owner's position; unresolved ownership prevents completeness certification. | ______ |

Confirmer / role: __________________  Confirmation date: __________________

Evidence/reference and approved effective date: ___________________________

Implementation keeps config/quota_rules.json PENDING. Changing that file alone
is insufficient: verified RAW coverage/state, dated live scope and compatible
units must also be supplied. Transaction creation choices are unchanged; the
new-entry list's mismatch with historical types/lease labels is a separate
decision, not permission to broaden daily validation.
