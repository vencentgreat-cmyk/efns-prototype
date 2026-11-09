"""Build design CSV/JSON from actual metadata; no database access or PII export."""

import argparse
import ast
from collections import defaultdict
import csv
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
GRAINS = {
    "ACCOUNT":"One business organization/account identity.",
    "CONTACT":"One contact identity, optionally linked to an Account.",
    "FARM_LOCATION":"One Account-owned farm-location identity.",
    "FACILITY":"One Account-owned facility/building identity; optional farm location.",
    "FACILITY_DETAIL":"One facility detail/history record, not another Facility identity.",
    "FLOCK":"One Flock identity with one optional Facility reference; multiple Flocks may share a Facility.",
    "FLOCK_TRANSACTION":"One recorded activity/transaction referring to a Flock.",
    "SALMONELLA_TEST":"One test identity; test and Flock Account roles remain distinct.",
    "SALMONELLA_TEST_SAMPLE":"One sample record belonging to one test; not one sample per test by rule.",
    "QUOTA_REGISTRATION":"One quota registration identity; historical registration number may be unknown.",
    "QUOTA_TRANSACTION":"One quota transaction identity; related quota and related transaction are separate roles.",
    "QUOTA_ALLOCATION":"One historical allocation identity; no Account FK is declared.",
    "DIM_EFC_DATE":"One distinct DAY target; multiple original date source rows can map to it.",
    "PRODUCTION_RECORD":"One source/manual production observation; source GUID identifies historical marketing rows.",
    "PRODUCTION_SIZE_BREAKDOWN":"One size-band child row for a production record; historical wide sizes are separate storage.",
    "IMPORT_BATCH":"One production/operational import tracking identity.",
    "IMPORT_RAW_ROW":"One preserved production/operational upload source row.",
    "MIGRATION_BATCH":"One historical package batch, not one daily upload.",
    "MIGRATION_FILE":"One source-file metadata record within a historical batch.",
    "MIGRATION_RAW_ROW":"One original source row identified by batch plus RAW row ID.",
    "MIGRATION_ID_MAP":"One Ready source-row lineage; many date lineages may share a DAY target.",
    "MIGRATION_ERROR":"One validation or runtime error record; multiple errors may refer to a source row.",
    "MIGRATION_RECONCILIATION":"One batch/entity summary, not a target record.",
    "MIGRATION_CORRECTION_BATCH":"One independent correction attempt/batch linked to an original historical batch.",
    "MIGRATION_CORRECTION_ROW":"One source-row correction/review trace within a correction batch.",
    "AUDIT_EVENT":"One audit event; ENTITY_ID is a polymorphic text reference, not a declared business FK.",
    "APP_USER":"One application user/security identity.",
}
EXCEPTIONS = {
    "QUOTA_REGISTRATION":"Historical REGISTRATION_NUMBER may be null; daily entry remains separately validated.",
    "QUOTA_TRANSACTION":"Historical signed/zero QUOTA_COUNT is preserved; missing-parent records remain pending.",
    "FLOCK":"Historical nullable Facility/dates are preserved; negative BIRDS_DISPOSED is not rewritten. Account mismatch remains pending.",
    "SALMONELLA_TEST":"Historical nullable sample count/result and distinct test/Flock Accounts are permitted if references exist.",
    "PRODUCTION_RECORD":"Historical signed values and SOURCE_WEEK_CODE are retained; TOTAL is not TOTAL_RECEIVED.",
}
DEFINITIONS = {
    'CREATED_AT':'Recorded creation timestamp. Repository writes explicitly use UTC; historical NTZ provenance may be unverified.',
    'UPDATED_AT':'Recorded last modification timestamp. Historical naive values are not automatically interpreted as UTC.',
    'COMMITTED_AT':'Timestamp recorded only when the batch transaction successfully commits; historical NTZ basis may be unverified.',
    'OCCURRED_AT':'Audit event timestamp, stored with timezone/offset.',
    'ACTOR_USER_ID':'Application actor identifier retained by the audit writer; no declared user FK.',
    'ACTOR_EMAIL':'Email identifier supplied by the application audit writer for the actor.',
    'ACTION':'Audit operation name supplied by application authorization/audit code.',
    'ENTITY_ID':'Polymorphic audit reference to the affected record/import/batch; VARCHAR(1000), not a universal FK.',
    'ENTITY_TYPE':'Name of the entity/operation category recorded with the audit event.',
    'PACKAGE_HASH':'Hash of the historical source package used to recognize repeated preparation.',
    'FILE_HASH':'SHA-256 file-content hash used for import lineage/duplicate detection.',
    'SOURCE_FILENAME':'Recorded source filename; original historical filenames are retained.',
    'SOURCE_ROW_NUMBER':'Persisted source-row ordinal; header/Excel basis depends on the loader, not inferred from this number alone.',
    'SOURCE_ID':'Normalized original entity key as text (GUID or ISO DAY); not the complete RAW source-row identity.',
    'TARGET_ID':'Business target key as text, including ISO DAY for date targets; repeated date source rows may share it.',
    'MIGRATION_RAW_ROW_ID':'Stable batch-local source-row identity; combine with original migration batch, never use unscoped.',
    'VALIDATION_STATUS':'Saved row-validation result, separate from transaction/batch commit status.',
    'MATCH_STATUS':'Recorded matching state; does not imply an unverified relationship is approved.',
    'VALIDATION_MESSAGES':'Preserved list of validation reasons for the source row.',
    'ERROR_CATEGORY':'Class of validation/runtime failure; original validation history remains intact.',
    'ERROR_MESSAGE':'Persisted sanitized failure reason; not a substitute for original source payload.',
    'DISPOSITION':'Correction classification: eligible, pending, or already committed in the preview; stored correction history retained.',
    'RELATION_STATUS':'Whether required relationships have been verified, separate from preserving a historical row.',
    'REASON':'Recorded correction/review classification rationale.',
    'STAGE_PATH':'Internal-stage location of the preserved uploaded source file.',
    'SCHEMA_VERSION':'Versioned historical mapping/parser contract used to prepare the batch.',
    'FULL_NAME':'Stored contact display name; CONTACT is a list, separate from Account primary contact fields.',
    'CONTACT_NAME':'Account primary contact text, not an authoritative synchronization link to CONTACT.',
    'CONTACT_PHONE':'Account primary contact phone text, separate from CONTACT records.',
    'CONTACT_EMAIL':'Account primary contact email text, separate from CONTACT records.',
    'ORGANIZATION_NAME':'Account organization display name; not a primary or deduplication key.',
    'REGISTRATION_NUMBER':'Business registration number; daily requiredness and historical quota exceptions are distinct.',
    'FLOCK_NUMBER':'Flock display/business number; historical fallback is efc_flocknumber, new_name, then source GUID.',
    'PLACEMENT_DATE':'Recorded placement date if known; overlapping Flocks at one Facility are allowed.',
    'DISPOSAL_DATE':'Recorded disposal date if known; does not independently prove full occupancy ended.',
    'EST_DISPOSAL':'Estimated disposal date; never substituted for an actual end date.',
    'BIRD_COUNT':'Recorded registered Flock bird count, not a verified current-inventory calculation.',
    'BIRDS_DISPOSED':'Recorded disposal measure; signed historical values are preserved and not automatically inventory deductions.',
    'QUOTA_COUNT':'Recorded quota transaction quantity; signed/zero history is preserved, not an available-quota balance.',
    'SOURCE_WEEK_CODE':'Original production period encoding; legacy CYYWW and YYYYWW parser derivation does not establish EFC-period mapping.',
    'DAY':'Unique target calendar day. Multiple source rows/ElementCodes can map to this DAY without being discarded.',
    'NUMBER_OF_SAMPLES':'Recorded test sample-count value; historical null allowed, not necessarily the current child-row count.',
}


def csv_file(path, rows):
    if not rows:
        return
    with path.open("w",encoding="utf-8-sig",newline="") as handle:
        writer=csv.DictWriter(handle,fieldnames=list(dict.fromkeys(k for row in rows for k in row)))
        writer.writeheader()
        writer.writerows(rows)


def build(source, output):
    output.mkdir(parents=True,exist_ok=True)
    metadata=json.loads(source.read_text(encoding="utf-8"))
    mapping=json.loads((ROOT/"config/eims_migration_mapping_v3.json").read_text(encoding="utf-8"))
    keys=defaultdict(list)
    for category in ("pks","uks"):
        for row in metadata[category]:
            keys[(row["schema_name"],row["table_name"],row["column_name"])].append(category[:-1].upper()+":"+row["constraint_name"])
    fk_groups=defaultdict(list)
    for row in metadata["fks"]:
        fk_groups[(row["fk_schema_name"],row["fk_table_name"],row["fk_name"])].append(row)
        keys[(row["fk_schema_name"],row["fk_table_name"],row["fk_column_name"])].append("FK:"+row["fk_name"]+" -> "+row["pk_schema_name"]+"."+row["pk_table_name"]+"."+row["pk_column_name"])
    code_files=list((ROOT/"app").rglob("*.py"))+list((ROOT/"data").rglob("*.py"))
    code={str(p.relative_to(ROOT)).replace('\\','/'):p.read_text(encoding="utf-8-sig") for p in code_files}
    dictionary=[]
    usage=[]
    for row in metadata["field_usage"]:
        schema,table,field=row["TABLE_SCHEMA"],row["TABLE_NAME"],row["COLUMN_NAME"]
        spec=mapping["entities"].get(table,{}) if schema=="CORE" else {}
        source_field=spec.get("field_map",{}).get(field)
        fallback=spec.get("fallbacks",{}).get(field,[])
        refs=[p for p,text in code.items() if re.search(r"\b"+re.escape(field)+r"\b",text)]
        constraint="; ".join(keys[(schema,table,field)])
        definition=("Declared reference: "+constraint if "FK:" in constraint else
                    "Record identity: "+constraint if "PK:" in constraint else
                    "Original source field "+str(source_field)+" retained in "+table+"."+field if source_field else
                    "Stored "+row["DATA_TYPE"]+" attribute "+table+"."+field+"; see named code/DDL evidence.")
        status="Technical definition verified; business meaning/units require EFNS confirmation"
        if field in DEFINITIONS:
            definition=DEFINITIONS[field]
            status='Definition supported by current code/schema; unconfirmed business interpretations remain separate'
        if field in {"REPORTING_YEAR","REPORTING_WEEK"}:
            definition="Reporting period component; historical SOURCE_WEEK_CODE parsed by data/migration.py."
            status="Technical conversion verified; EFC-period attribution is not inferred."
        elif field in {"RAW_DATA","NORMALIZED_DATA","CORRECTED_DATA"}:
            definition={"RAW_DATA":"Unmodified original row payload.","NORMALIZED_DATA":"Parsed values for migration validation/target writes.","CORRECTED_DATA":"Independent corrected/review payload; original RAW is not overwritten."}[field]
            status="Technical definition verified"
        elif field=="TOTAL" and table in {"PRODUCTION_RECORD","VW_PRODUCTION_SUMMARY"}:
            definition="Source Total; original TOTAL only, not replaced by received/accepted quantities."
        expression=""
        if schema=="REPORTING":
            ddl=metadata["ddl"][schema+"."+table]
            # All four deployed views have simple comma-separated projections.
            # Accept only those exact simple expressions; do not guess complex SQL.
            select=re.search(r"\bAS\s+SELECT\s+(.*?)\s+FROM\s",ddl,re.I|re.S)
            if select:
                for item in select.group(1).split(','):
                    item=item.strip()
                    alias=re.match(r"(?:\w+\.\w+)(?:\s+AS\s+(\w+))?$",item,re.I)
                    if alias and (alias.group(1) or item.split('.')[-1]).upper()==field:
                        expression=item
            definition="View output; deployed expression: "+(expression or "To be verified; consult exported GET_DDL")
            status="Expression verified from actual GET_DDL" if expression else "To be verified"
        dtype=row["DATA_TYPE"]
        if row["CHARACTER_MAXIMUM_LENGTH"] is not None:
            dtype+=f'({row["CHARACTER_MAXIMUM_LENGTH"]})'
        elif row["NUMERIC_PRECISION"] is not None:
            dtype+=f'({row["NUMERIC_PRECISION"]},{row["NUMERIC_SCALE"]})'
        elif dtype.startswith('TIMESTAMP'):
            precision=row.get('DATETIME_PRECISION')
            if precision is not None:
                dtype+='('+str(precision)+')'
            else:
                declared=re.search(r'\b'+re.escape(field)+r'\s+'+dtype+r'\((\d+)\)',metadata['ddl'][schema+'.'+table],re.I)
                if declared:
                    dtype+='('+declared.group(1)+')'
        check="BIRD_COUNT >= 0 (database CHECK)" if table=="FLOCK" and field=="BIRD_COUNT" else ""
        entry={
            "Schema":schema,"Table":table,"Column":field,"Business label":field.replace('_',' ').title(),
            "Definition":definition,"SQL type":dtype,"Nullable":row["IS_NULLABLE"],
            "Default":row["COLUMN_DEFAULT"],"Declared keys":constraint,"Declared CHECK":check,
            "Enforcement":"Standard table PK/FK/UNIQUE informational; NOT NULL/CHECK enforced; application rules separate" if schema!="REPORTING" else "View output; no table key enforcement",
            "Source file":spec.get("filename",""),"Source field":source_field or "",
            "Fallbacks":json.dumps(fallback) if fallback else "","Unit/code meaning":"Requires EFNS confirmation" if row["DATA_TYPE"]=="NUMBER" or field.endswith(("_TYPE","STATUS","RESULT")) else "Not applicable or not independently confirmed",
            "Historical exception":EXCEPTIONS.get(table,""),"Code evidence":"; ".join(refs),
            "Metadata evidence":str(source),"Business confirmation":status,"View expression":expression,
        }
        dictionary.append(entry)
        usage.append({"Schema":schema,"Table":table,"Column":field,"Declared keys":constraint,
            "Row count":row["ROW_COUNT"],"Non-null count":row["NON_NULL_COUNT"],"Zero count":row["ZERO_COUNT"],
            "Form reference":any('/pages/' in p for p in refs),
            "Import reference":any('import' in p or 'migration' in p or 'correction' in p for p in refs),
            "Validation reference":any('validation' in p for p in refs),
            "Query reference":any('/repositories/' in p for p in refs),
            "Report reference":any('report' in p.lower() for p in refs),
            "Category":"Relationship key" if constraint else "Source retention" if source_field else "Business/code-referenced field" if refs else "Currently unreferenced extension",
            "Usage evidence":'; '.join(refs),"Limitation":"Text reference is evidence of use somewhere, not proof of table-specific semantic use."})
    objects=[{"Schema":t["TABLE_SCHEMA"],"Object":t["TABLE_NAME"],"Type":t["TABLE_TYPE"],"Row grain":GRAINS.get(t["TABLE_NAME"],"Flattened view; grain determined by LEFT JOINs in exported DDL."),"Actual COMMENT":t["COMMENT"]} for t in metadata["tables"]]
    csv_file(output/"data_dictionary.csv",dictionary)
    csv_file(output/"field_usage.csv",usage)
    csv_file(output/"object_inventory.csv",objects)
    csv_file(output/"column_inventory.csv",metadata["columns"])
    csv_file(output/"constraint_inventory.csv",metadata["constraints"])
    csv_file(output/"integrity.csv",metadata["integrity"])
    (output/"actual_get_ddl.sql").write_text('-- METADATA SNAPSHOT ONLY. DO NOT EXECUTE. GET_DDL CREATE OR REPLACE output is not a deployment script.\n\n'+'\n\n'.join('-- '+name+'\n'+ddl for name,ddl in metadata["ddl"].items()),encoding="utf-8")
    tables=[]
    simple=[]
    for obj in metadata["tables"]:
        schema,table=obj["TABLE_SCHEMA"],obj["TABLE_NAME"]
        if obj["TABLE_TYPE"]=="VIEW":
            continue
        pk=[r["column_name"] for r in sorted(metadata["pks"],key=lambda r:r["key_sequence"]) if r["schema_name"]==schema and r["table_name"]==table]
        cols=[c for c in dictionary if c["Schema"]==schema and c["Table"]==table]
        tables.append({"schema":schema,"name":table,"primary_key":pk,"row_grain":GRAINS[table],"columns":cols})
        key_cols=[c["Column"] for c in cols if c["Declared keys"]]
        representative=[c["Column"] for c in cols if c["Column"] not in key_cols and c["Column"] not in {"CREATED_AT","UPDATED_AT"}][:3]
        simple.append({"Schema":schema,"Table":table,"Keys":', '.join(key_cols),"Representative fields":', '.join(representative),"Other fields":"Additional attributes omitted"})
    relations=[]
    for (schema,table,name),members in fk_groups.items():
        members.sort(key=lambda r:r["key_sequence"])
        child=next(t for t in tables if t["schema"]==schema and t["name"]==table)
        columns=[r["fk_column_name"] for r in members]
        unique_groups=defaultdict(set)
        for key in metadata['uks']+metadata['pks']:
            if key['schema_name']==schema and key['table_name']==table:
                unique_groups[key['constraint_name']].add(key['column_name'])
        child_unique=any(group.issubset(set(columns)) for group in unique_groups.values())
        optional=any(c['Nullable']=='YES' for c in child['columns'] if c['Column'] in columns)
        relations.append({"name":name,"child":schema+'.'+table,"child_columns":columns,
            "parent":members[0]["pk_schema_name"]+'.'+members[0]["pk_table_name"],"parent_columns":[r["pk_column_name"] for r in members],
            "optional":optional,"parent_cardinality":"0..1" if optional else "1",
            "child_cardinality":"0..1" if child_unique else "0..many",
            "identifying":all(c in child["primary_key"] for c in columns),"enforced":False})
    spec={"metadata_source":str(source),"tables":tables,"foreign_keys":relations,
        "style":{"non_identifying":"dashed","identifying":"solid","repeated_table":"solid border, grey fill","self_reference":"loop labelled by FK fields"},
        "notes":["Composite keys are one key group and one FK relationship.","RAW batch FK is now identifying because batch belongs to composite RAW PK.","No invented FK for QUOTA_ALLOCATION or DIM_EFC_DATE.","Facility may host successive/concurrent Flocks; cross-Account hosting remains unconfirmed."]}
    (output/"erd_spec.json").write_text(json.dumps(spec,indent=2),encoding="utf-8")
    csv_file(output/"simplified_erd_fields.csv",simple)
    # Export actual validation definitions, not a stale numbered-rule count.
    rules=[]
    for relative in ("data/validation.py","data/importing.py","data/migration.py","data/historical_corrections.py","data/operational_flock_quota_import.py"):
        text=(ROOT/relative).read_text(encoding="utf-8-sig")
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and any(word in node.name for word in ("validat","normaliz","parse","required")):
                rules.append({"Rule implementation":node.name,"Scope":relative,"Line":node.lineno,"Description":ast.get_docstring(node) or "See function implementation; technical rule, not independent business confirmation.","Evidence":relative+':'+str(node.lineno)})
    csv_file(output/"effective_rule_implementations.csv",rules)
    from data.migration import _field_types
    catalog=[]
    for entity,contract in mapping['entities'].items():
        for field,kind in _field_types(contract).items():
            catalog.append({'Scope':'Historical v3','Entity':entity,'Field':field,'Rule':'Parse '+kind,'Condition':'If populated; null placeholders normalized','Evidence':'config/eims_migration_mapping_v3.json / data/migration.py','Business confirmation':'Technical parser rule, not a unit/formula definition'})
        for field in contract.get('required',[]):
            catalog.append({'Scope':'Historical v3','Entity':entity,'Field':field,'Rule':'Required','Condition':'Historical preparation; confirmed exceptions handled separately','Evidence':'config/eims_migration_mapping_v3.json','Business confirmation':'Historical contract; daily requiredness is separate'})
        for field,parent in contract.get('foreign_keys',{}).items():
            catalog.append({'Scope':'Historical v3','Entity':entity,'Field':field,'Rule':'Reference '+'.'.join(parent),'Condition':'If populated; missing parent rejected/preserved for review, not fabricated','Evidence':'config/eims_migration_mapping_v3.json / data/migration.py','Business confirmation':'Technical relationship existence check'})
        for field,rule in contract.get('numeric_rules',{}).items():
            catalog.append({'Scope':'Historical v3','Entity':entity,'Field':field,'Rule':json.dumps(rule,sort_keys=True),'Condition':'If populated; signed exceptions not inferred into balances','Evidence':'config/eims_migration_mapping_v3.json','Business confirmation':'Technical contract, not a business balance'})
        for field,choices in contract.get('choices',{}).items():
            catalog.append({'Scope':'Historical v3','Entity':entity,'Field':field,'Rule':'Allowed choices: '+json.dumps(choices),'Condition':'If populated','Evidence':'config/eims_migration_mapping_v3.json','Business confirmation':'Accepted display values, not independently confirmed business operations'})
    for relative in ('data/validation.py','data/migration_identity.py'):
        text=(ROOT/relative).read_text(encoding='utf-8-sig')
        for node in ast.walk(ast.parse(text)):
            if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='append' and node.args and isinstance(node.args[0],(ast.Constant,ast.JoinedStr)):
                if isinstance(node.args[0],ast.Constant) and not isinstance(node.args[0].value,str):
                    continue
                catalog.append({'Scope':'Daily application validation' if 'validation.py' in relative else 'Source identity protection','Entity':'See code context','Field':'See code context','Rule':ast.unparse(node.args[0]),'Condition':'Branch condition in cited implementation','Evidence':relative+':'+str(node.lineno),'Business confirmation':'Implemented check; confirmation status remains in BUSINESS_RULES.md'})
            elif isinstance(node,ast.Raise) and isinstance(node.exc,ast.Call) and node.exc.args and isinstance(node.exc.args[0],(ast.Constant,ast.JoinedStr)):
                catalog.append({'Scope':'Daily application validation' if 'validation.py' in relative else 'Source identity protection','Entity':'See code context','Field':'See code context','Rule':ast.unparse(node.exc.args[0]),'Condition':'Branch condition in cited implementation','Evidence':relative+':'+str(node.lineno),'Business confirmation':'Implemented guard; no fabricated parent or unit'})
    csv_file(output/'effective_rule_catalog.csv',catalog)
    sheets={"Objects":objects,"Table dictionary":[r for r in dictionary if r["Schema"]!="REPORTING"],"View dictionary":[r for r in dictionary if r["Schema"]=="REPORTING"],"Rule catalog":catalog,"Field usage":usage}
    (output/"workbook_data.json").write_text(json.dumps(sheets,default=str,indent=2),encoding="utf-8")
    (output/"erd_validation.json").write_text(json.dumps({"tables":len(tables),"relationships":len(relations),"columns":len(dictionary),"table_columns":len(sheets["Table dictionary"]),"view_columns":len(sheets["View dictionary"]),"view_expressions_verified":sum(bool(c["View expression"]) for c in sheets["View dictionary"]),"basis":"Actual post-repair metadata; complete composite groups preserved"},indent=2),encoding="utf-8")
    print((output/"erd_validation.json").read_text())


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    build(args.source,args.output)
