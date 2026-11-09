# Current Rule Delta

The retained 13 October catalog is historical context, not a claim that no rules changed. Add these implementation-backed rules:

- Production manual entry requires an existing producer Account; unresolved source uploads can remain RAW/pending without a fictitious Account.
- Producer matching uses exact GUID/registration comparison. AUTO never sets human confirmation; explicit staff confirmation sets who/when/basis.
- Producer grouping is source-scoped without Account attribution; identity-less rows retain independent record identities. NULL sum uses min_count=1.
- Original archive is byte-exact and checksum verified. Parse success and row validation/CORE commit are separate states.
- Nonempty workbook rows missing identity are retained. Operational unsupported/rejected rows are staged without CORE writes.
- Prepared operational writes must match the saved normalized review; target identity is planned until batch/target checks prove commit.
- Whole-Flock movement requires evidence confirmation, explicit time/reason/recorder, existing same-Account destination, chronological event history and request-id retry protection.
- Estimated disposal never creates an actual end. End retains last recorded Facility reference; history queries use explicit events, not extrapolated placement dates.
- Multiple simultaneous/successive Flocks in one Facility remain allowed. Cross-Account and partial quantity rules are not assumed.
- Attribute/quantity corrections append snapshots and reasons; ordinary Flock updates cannot silently replace actual movement/end history.
- New intake/history writes serialize on the provisioned control row; missing/duplicate lock fails closed. Existing optimistic locking remains.

See data/repositories/continuity.py, data/production_intake.py, data/producer_identity.py, data/operational_flock_quota_import.py and app/services/report_center.py for implementations. Historical v3 mapping/rejection rules and the complete-package contract remain unchanged.
