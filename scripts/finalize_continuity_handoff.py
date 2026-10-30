"""Package only technical evidence/documentation, never originals or credentials."""
import json
import shutil
from pathlib import Path
import zipfile

root=Path(__file__).resolve().parents[1]
out=root/'docs/identity_history_2026-10-14'
private=root/'.local/continuity-20261014'
verified=json.loads((private/'deployed_verification/deployed_verification.json').read_text(encoding='utf-8'))
runtime=json.loads((private/'dev_runtime_checks.json').read_text(encoding='utf-8'))
summary={
 'deployment':'Succeeded; original account RC34234 / EFNS_DEV',
 'source_files_verified':len(verified['deployed_files']),
 'context':verified['context'],
 'reconciliation':verified['reconciliation'],
 'reports':verified['reports'],
 'correction_preview':verified['correction_preview'],
 'temporary_dml_tests':{key:value for key,value in runtime.items() if key.startswith('temporary_') or key=='rollback'},
 'archive_byte_test':runtime['original_archive'],
 'browser_acceptance_this_round':False,
 'local_full_pytest':'463 passed; eight deprecation/future warnings',
 'readiness':'Passed','diff_check':'Passed',
 'new_page':'app/pages/21_Record_History.py',
 'unchanged_reference_page':'app/pages/20_EIMS_Reference_Data.py',
 'queries':verified['queries'],
}
(out/'Deployment_Verification_Summary.json').write_text(json.dumps(summary,default=str,indent=2),encoding='utf-8')
for source,name in [('recovered_workbook_check.json','Recovered_Workbook_Completeness.json'),('omitted_rows_recovery.json','RAW_Only_Supplement.json')]:shutil.copy2(private/source,out/name)
shutil.copy2(root/'sql/16_Source_Identity_and_Flock_History.sql',out/'Additive_DEV_Upgrade.sql')
shutil.copy2(root/'docs/database_manual_2026-10-13/metadata/effective_rule_catalog.csv',out/'Retained_Rule_Catalog_20261013.csv')
(out/'Current_Rule_Delta.md').write_text('''# Current Rule Delta

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
''',encoding='utf-8')
archive=out/'EFNS_Claude_Update_Handoff_2026-10-14.zip'
files=[p for p in out.iterdir() if p.is_file() and p!=archive and not p.name.endswith(('.inspect.ndjson','_preview.png','.mjs'))]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in files:z.write(p,p.name)
 # Preserve detailed existing diagrams as dated background, not current metadata.
 previous=root/'docs/database_manual_2026-10-13/erd'
 for p in previous.rglob('*'):
  if p.is_file() and p.suffix in {'.dot','.svg','.json'}:z.write(p,'Previous_ERD_20261013/'+str(p.relative_to(previous)).replace('\\','/'))
 z.writestr('Previous_ERD_20261013/READ_FIRST.txt','These retained detailed diagrams are the 13 October baseline. Actual_ERD_Spec.json and Complete_Actual_ERD.mmd are the current full 46-relationship specification. New tables/fields are not present in the baseline diagrams. Do not label old panels as the final complete schema.')
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert not any(name.endswith(('.xlsm','.xlsx')) and name!='Latest_Data_Dictionary.xlsx' for name in z.namelist())
print(json.dumps({'files':len(files),'zip_bytes':archive.stat().st_size,'source_files_verified':len(verified['deployed_files']),'reconciliation':verified['reconciliation']}))
