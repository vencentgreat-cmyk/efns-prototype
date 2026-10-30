"""Build a PII-free fact handoff from final DEV metadata and reviewed code."""
import csv
import html
import json
from pathlib import Path
import shutil
import zipfile
from collections import defaultdict
from build_design_handoff import GRAINS

ROOT=Path(__file__).resolve().parents[1]
PRIVATE=ROOT/'.local/continuity-20261014'
OUT=ROOT/'docs/identity_history_2026-10-14'
OUT.mkdir(parents=True,exist_ok=True)
e=json.loads((PRIVATE/'schema_after_final/dev_evidence.json').read_text(encoding='utf-8'))
before=json.loads((PRIVATE/'schema_before/dev_evidence.json').read_text(encoding='utf-8'))
old=json.loads((ROOT/'docs/database_manual_2026-10-13/metadata/enhanced_dictionary.json').read_text(encoding='utf-8'))
old={(r['Schema'],r['Table'],r['Column']):r for r in old}
inventory={(r['TABLE_SCHEMA'],r['TABLE_NAME']):r for r in e['tables']}
new_purpose={
 'SOURCE_FILE':'One unchanged archived original per route, filename and content digest; repeat attempts do not overwrite it.',
 'INTAKE_LOCK':'One provisioned transaction-control row. It is not a business/source record.',
 'PRODUCTION_MATCH_DECISION':'One recorded producer-resolution decision for a production identity; automatic and staff handling are distinct.',
 'FLOCK_EVENT':'One asserted movement or actual-end event; corrections append a superseding event, preserving earlier entries.',
 'RECORD_REVISION':'One attribute/quantity correction or parser-status transition, with before/after values; not a movement journal.',
}
definitions={
 'SOURCE_FILE_ID':'Stable archived-original identity derived from route, original filename and SHA-256; not a reconstructed RAW file.',
 'ORIGINAL_FILENAME':'Original uploaded filename, retained unchanged in metadata; stage object names use safe deterministic identifiers.',
 'FILE_HASH':'SHA-256 of unchanged original bytes. A batch package hash and a single-file digest have different scopes.',
 'FILE_SIZE_BYTES':'Length of unchanged original bytes, in bytes.',
 'STAGE_PATH':'Internal-stage object location; archive writes refuse overwrite and retrieval verifies SHA-256.',
 'IMPORT_ROUTE':'Recorded capture path, including explicitly marked isolated QA; not proof that business validation passed.',
 'PARSE_STATUS':'Current parser outcome: ARCHIVED, PARSED or PARSE_FAILED. Row validation is separate.',
 'PARSE_ERROR':'Sanitized parser failure explanation; original bytes remain retrievable. It is not a business-row rejection reason.',
 'UPLOADED_BY':'Initiating application user ID or clearly marked SYSTEM actor; NULL means unrecorded. Recovery captures the archival operator, not an inferred historic uploader.',
 'UPLOADED_AT':'UTC-naive archival capture time in new writes; for recovered files it is not the original historic upload time.',
 'MATCH_DECISION_ID':'Append-only decision identity; repeat producer resolution reuses its deterministic decision identity.',
 'SOURCE_PRODUCER_NUMBER':'Stored source producer number; no name-based matching and no fabricated number.',
 'PRODUCTION_ID':'Production record whose producer decision is recorded; one production record may have successive decisions, not duplicate observations.',
 'ACCOUNT_ID':'Proposed or selected existing Account for this decision; NULL means attribution has not been established.',
 'FLOCK_ID':'Existing Flock whose whole-position or actual-end event is recorded; multiple events preserve its lifecycle history.',
 'MATCH_STATUS':'Technical producer-resolution outcome. Legacy CONFIRMED does not prove staff confirmation. New states distinguish missing identity, no candidate, multiple candidates, unique automatic matching and staff confirmation.',
 'MATCH_METHOD':'Exact supplied GUID, exact stored registration number or explicit staff selection; automatic matching is not staff confirmation.',
 'MATCH_BASIS':'Recorded exact matching evidence or staff-provided explanation; it does not approve units or business formulas.',
 'HANDLING':'AUTO or STAFF; records how the decision was handled, not a claimed business approval.',
 'RECORDED_BY':'Authenticated initiating application user or explicit SYSTEM actor. This is not a declared FK to SECURITY.APP_USER.',
 'RECORDED_AT':'UTC-naive system recording time in the new writer; distinct from the effective business time.',
 'EVENT_ID':'Stable Flock event identity derived from Flock ID and request ID; repeated identical requests do not create another event.',
 'EVENT_TYPE':'MOVE or END. END denotes an asserted actual lifecycle end; estimated dates never create it.',
 'FROM_FACILITY_ID':'Recorded origin for a staff-asserted move; corrections retain the origin of the superseded event. For END, the last recorded reference is retained, not inferred past occupancy.',
 'TO_FACILITY_ID':'Destination of a whole-Flock MOVE; NULL for END. No partial-transfer quantity formula is asserted.',
 'EFFECTIVE_AT':'Explicit timezone-aware business timestamp converted to UTC-naive storage. Unknown past movements are not invented.',
 'SUPERSEDES_EVENT_ID':'Optional event being corrected, within the same Flock; the original event is retained.',
 'BEFORE_DATA':'JSON snapshot before the recorded operation; new evidence encoding preserves dates as ISO text and blank cells as JSON null.',
 'AFTER_DATA':'JSON snapshot after the operation; movement assertion metadata is explicit and does not fabricate original source values.',
 'REASON':'Operator explanation of the event/correction, not a generic replacement for business activity semantics.',
 'REVISION_ID':'Stable correction request identity; parser transitions append separate records.',
 'ENTITY_TYPE':'Polymorphic subject type (FLOCK, FACILITY or SOURCE_FILE in the new workflows); no inferred FK.',
 'ENTITY_ID':'Polymorphic subject identity, not a declared FK; normal source/business identifiers remain unchanged.',
 'CHANGE_KIND':'ATTRIBUTE_CORRECTION, QUANTITY_CORRECTION or PARSE_REVIEW. Flock movements and ends use FLOCK_EVENT instead.',
 'BUSINESS_AT':'Optional explicit business timestamp for an attribute correction; unknown effective time remains NULL.',
 'LOCK_ID':'Provisioned continuity control identity. Writers refuse operation if the control row is missing/duplicated.',
 'VERSION':'Transaction-control counter updated to obtain a cross-session row lock; not an object business version.',
 'TARGET_ENTITY':'Polymorphic planned target table/entity for a prepared source row. Batch commit and target existence must be checked before calling it materialized.',
 'TARGET_ID':'Stable planned target GUID for an accepted source row; invalid/unsupported rows have no target. It is not a declared polymorphic FK.',
 'RAW_ROW_ID':'Parsed-source row identity. New production intake stores its RAW pointer; source file, batch and physical row retain the trace.',
}
special_tables=set(new_purpose)
changed_fields={'SOURCE_FILE_ID','RAW_ROW_ID','MATCH_METHOD','MATCH_BASIS','TARGET_ENTITY','TARGET_ID'}
keymap=defaultdict(list)
for category,label in [('pks','PK'),('uks','UNIQUE')]:
 for row in e[category]:keymap[(row['schema_name'],row['table_name'],row['column_name'])].append(label+':'+row['constraint_name'])
for row in e['fks']:
 keymap[(row['fk_schema_name'],row['fk_table_name'],row['fk_column_name'])].append(f"FK:{row['fk_name']} -> {row['pk_schema_name']}.{row['pk_table_name']}.{row['pk_column_name']}")
usage={(r['TABLE_SCHEMA'],r['TABLE_NAME'],r['COLUMN_NAME']):r for r in e['field_usage']}
dictionary=[]
for column in e['columns']:
 key=tuple(column[k] for k in ('TABLE_SCHEMA','TABLE_NAME','COLUMN_NAME'))
 schema,table,name=key
 prior=old.get(key,{})
 definition=prior.get('Definition') or definitions.get(name) or f'Technical {name} attribute; business meaning requires EFNS confirmation.'
 changed=table in special_tables or (table in {'PRODUCTION_RECORD','IMPORT_RAW_ROW','IMPORT_BATCH','VW_PRODUCTION_SUMMARY'} and name in changed_fields|{'IMPORT_ID','MATCH_STATUS','MATCH_CONFIRMED_AT','MATCH_CONFIRMED_BY'})
 if changed and name in definitions:definition=definitions[name]
 if name=='TOTAL' and table in {'PRODUCTION_RECORD','VW_PRODUCTION_SUMMARY'}:
  definition='Original source Total: historical v3 efc_total; workbook heading Total; manual Source Total input. These are separate contracts. Never substitute TOTAL_RECEIVED or TOTAL_ACCEPTED; unknown remains NULL and historical signed values are retained.'
 sqltype=column['DATA_TYPE']
 if sqltype=='TEXT':sqltype+=f"({column['CHARACTER_MAXIMUM_LENGTH']})"
 elif sqltype=='NUMBER':sqltype+=f"({column['NUMERIC_PRECISION']},{column['NUMERIC_SCALE']})"
 source=prior.get('Source and transformation','')
 evidence=prior.get('Code evidence','')
 if changed:
  source='ContinuityRepository source-evidence/producer/event/revision writer; SOURCE_FILE_ID and RAW_ROW_ID are generated evidence identities, never fabricated source business values.'
  evidence='data/repositories/continuity.py; data/production_intake.py; data/producer_identity.py; data/repositories/snowflake.py'
 if table=='FLOCK_EVENT':source='record_flock_event: explicit operator request, reason, timezone-aware business time; no generated past movement.'
 if table=='SOURCE_FILE':source='archive_source_file: unchanged input bytes; put_stream(auto_compress=False, overwrite=False), get_stream and SHA-256 verification.'
 if table=='PRODUCTION_MATCH_DECISION':source='match_production_producer / commit_staged_production / create_manual_production; automatic decisions do not set staff-confirmed fields.'
 if table=='RECORD_REVISION':source='revise_record or authenticated record_source_parse; append-only snapshots, not an inferred movement/quantity formula.'
 if table=='INTAKE_LOCK':source='Provisioned by sql/16; _continuity_transaction updates the single control row before new intake/history writes.'
 if table=='VW_PRODUCTION_SUMMARY' and name in changed_fields|{'IMPORT_ID'}:source=f'Actual deployed view expression pr.{name}, from CORE.PRODUCTION_RECORD; LEFT JOIN Import Batch remains optional.'
 if table=='PRODUCTION_RECORD' and name in {'MATCH_CONFIRMED_AT','MATCH_CONFIRMED_BY'}:
  definition='Set only by explicit staff producer confirmation/manual entry in the new flow. Automatic matching leaves these fields unconfirmed; past unknown confirmation details remain unknown.'
 constraints='; '.join(keymap[key]) or 'No declared key membership'
 counts=usage[key]
 dictionary.append({'Schema':schema,'Table':table,'Column':name,'Object kind':inventory[(schema,table)]['TABLE_TYPE'],
  'Definition':definition,'SQL type':sqltype,'Nullable':column['IS_NULLABLE'],'Default':column['COLUMN_DEFAULT'] if column['COLUMN_DEFAULT'] is not None else 'No default declared',
  'Declared keys':constraints,'Source and transformation':source,'Units and codes':prior.get('Unit/code meaning','Technical identity/metadata; no unverified business unit or formula asserted.'),
  'Historical exception':prior.get('Historical exception',''),'Code evidence':evidence,
  'Metadata evidence':f'Final DEV GET_DDL and column_inventory: {schema}.{table}.{name}; captured {e["captured_at_utc"]}',
  'Non-null count':counts['NON_NULL_COUNT'],'Zero count':counts['ZERO_COUNT'],'Object rows':counts['ROW_COUNT']})
def csvfile(name,rows):
 if not rows:return
 keys=list(dict.fromkeys(key for row in rows for key in row))
 with (OUT/name).open('w',newline='',encoding='utf-8-sig') as f:
  writer=csv.DictWriter(f,fieldnames=keys);writer.writeheader();writer.writerows(rows)
csvfile('Latest_Data_Dictionary.csv',dictionary)
(OUT/'Latest_Data_Dictionary.json').write_text(json.dumps(dictionary,ensure_ascii=False,indent=2),encoding='utf-8')
csvfile('Column_Inventory.csv',e['columns']);csvfile('Declared_Constraints.csv',e['constraints']);csvfile('Declared_Foreign_Keys.csv',e['fks']);csvfile('Integrity_Checks.csv',e['integrity'])
objects=[]
for obj in e['tables']:
 table=obj['TABLE_NAME'];schema=obj['TABLE_SCHEMA']
 purpose=new_purpose.get(table)
 if not purpose:
  prior=next((r for key,r in old.items() if key[:2]==(schema,table)),{})
  purpose=GRAINS.get(table) or prior.get('Table purpose') or obj.get('COMMENT') or 'Reporting output; row grain follows its actual deployed view expression.'
 objects.append(dict(Schema=schema,Table=table,Kind=obj['TABLE_TYPE'],Purpose=purpose,Rows=next((r['ROW_COUNT'] for r in e['field_usage'] if r['TABLE_SCHEMA']==schema and r['TABLE_NAME']==table),None)))
csvfile('Object_Inventory.csv',objects)
(OUT/'Actual_Get_DDL.sql').write_text('\n\n'.join(f'-- {name}\n{ddl}' for name,ddl in e['ddl'].items()),encoding='utf-8')
spec={'objects':e['tables'],'columns':e['columns'],'primary_keys':e['pks'],'foreign_keys':e['fks'],'unique_keys':e['uks'],'source':'Final actual DEV metadata; do not infer FKs from names'}
(OUT/'Actual_ERD_Spec.json').write_text(json.dumps(spec,default=str,indent=2),encoding='utf-8')
groups=defaultdict(list)
for row in e['fks']:groups[(row['fk_schema_name'],row['fk_table_name'],row['fk_name'])].append(row)
erd=['erDiagram']
for obj in e['tables']:
 if obj['TABLE_TYPE']=='VIEW':continue
 node=obj['TABLE_SCHEMA']+'_'+obj['TABLE_NAME'];erd.append(f'    {node} {{')
 for c in e['columns']:
  if (c['TABLE_SCHEMA'],c['TABLE_NAME'])!=(obj['TABLE_SCHEMA'],obj['TABLE_NAME']):continue
  flags=keymap[(c['TABLE_SCHEMA'],c['TABLE_NAME'],c['COLUMN_NAME'])]
  marker=' PK' if any(s.startswith('PK:') for s in flags) else ' FK' if any(s.startswith('FK:') for s in flags) else ''
  erd.append(f'        {c["DATA_TYPE"]} {c["COLUMN_NAME"]}{marker}')
 erd.append('    }')
for (schema,table,name),members in groups.items():
 members.sort(key=lambda r:r['key_sequence']);parent=members[0]
 optional=any(next(c for c in e['columns'] if (c['TABLE_SCHEMA'],c['TABLE_NAME'],c['COLUMN_NAME'])==(schema,table,m['fk_column_name']))['IS_NULLABLE']=='YES' for m in members)
 left='|o' if optional else '||'
 fields=', '.join(m['fk_column_name'] for m in members)
 erd.append(f'    {parent["pk_schema_name"]}_{parent["pk_table_name"]} {left}..o{{ {schema}_{table} : "{fields}"')
(OUT/'Complete_Actual_ERD.mmd').write_text('\n'.join(erd),encoding='utf-8')
preserved={name:before['preservation'][name]==e['preservation'][name] for name in before['preservation']}
tablecount=sum(o['TABLE_TYPE']!='VIEW' for o in e['tables']);viewcount=len(e['tables'])-tablecount
tablecols=sum(r['Object kind']!='VIEW' for r in dictionary)
summary=dict(captured_at=e['captured_at_utc'],tables=tablecount,table_columns=tablecols,views=viewcount,view_columns=len(dictionary)-tablecols,field_entries=len(dictionary),foreign_key_relationships=len(groups),preservation=preserved,integrity_issues=[row for row in e['integrity'] if row.get('DUPLICATE_GROUPS',0) or row.get('ORPHAN_ROWS',0)])
(OUT/'Coverage_and_Preservation.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
assert all(preserved.values()) and not summary['integrity_issues']
csvfile('Migration_Batch_Status.csv',e['batch_status']);csvfile('Correction_Status.csv',e['corrections']);csvfile('Migration_Lineages.csv',e['lineages'])
applied=json.loads((PRIVATE/'applied_evidence_archive_retry.json').read_text(encoding='utf-8'))
csvfile('Verified_Original_Archive_Manifest.csv',applied['archives']);csvfile('Legacy_Original_File_Gaps.csv',applied['original_gaps'])
lines=['# Complete Current Data Dictionary','',f'Actual DEV snapshot: {e["captured_at_utc"]}. {tablecount} tables / {tablecols} table columns; {viewcount} views / {len(dictionary)-tablecols} outputs.','',
 'Unknown quantities are not zero. No default declared differs from an explicit SQL NULL default. Keys below are actual declarations; enforcement is recorded in Declared_Constraints.csv, not inferred from a diagram. Technical source facts do not approve units or formulas.','',
 'The 13 October manual remains evidence for unchanged business explanations, not current counts. Actual metadata here supersedes its structural inventories. New technical workflows are explained in Documentation_Update_Handoff.md.','']
for obj in objects:
 rows=[r for r in dictionary if r['Schema']==obj['Schema'] and r['Table']==obj['Table']]
 lines += [f'## {obj["Schema"]}.{obj["Table"]}',obj['Purpose'],'', '| Field | Type | Nullable | Default | Declared keys |','|---|---|---|---|---|']
 for r in rows:lines.append('| '+' | '.join(str(r[k]).replace('|',' / ').replace('\n',' ') for k in ['Column','SQL type','Nullable','Default','Declared keys'])+' |')
 lines += ['','### Definitions and Sources','', '| Field | Definition | Source / evidence |','|---|---|---|']
 for r in rows:lines.append('| '+' | '.join(str(value).replace('|',' / ').replace('\n',' ') for value in [r['Column'],r['Definition'],r['Source and transformation']+'; '+r['Code evidence']])+' |')
 lines.append('')
(OUT/'Complete_Current_Dictionary.md').write_text('\n'.join(lines),encoding='utf-8')
(OUT/'Complete_Current_Dictionary.html').write_text('<!doctype html><meta charset="utf-8"><style>body{font:15px Arial;max-width:1250px;margin:30px auto}table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:8px;vertical-align:top}th{background:#e9eeee}section{margin:35px 0}</style><h1>EFNS Current Dictionary</h1>'+''.join('<section><h2>'+html.escape(obj['Schema']+'.'+obj['Table'])+'</h2><p>'+html.escape(obj['Purpose'])+'</p><table><tr><th>Field</th><th>Technical metadata</th><th>Definition and source</th></tr>'+''.join('<tr><td>'+html.escape(r['Column'])+'</td><td>'+html.escape(r['SQL type']+'; nullable '+r['Nullable']+'; '+str(r['Default'])+'; '+r['Declared keys'])+'</td><td>'+html.escape(r['Definition']+' Source: '+r['Source and transformation'])+'</td></tr>' for r in dictionary if r['Schema']==obj['Schema'] and r['Table']==obj['Table'])+'</table></section>' for obj in objects),encoding='utf-8')
print(json.dumps(summary))
