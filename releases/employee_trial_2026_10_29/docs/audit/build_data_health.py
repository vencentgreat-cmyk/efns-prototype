"""Offline generator; reads checked-in definitions, writes only audit health SQL."""
from pathlib import Path
import ast,re
ROOT=Path(__file__).resolve().parents[2]

def build():
    tables={}
    for name in ('02_core_tables.sql','03_production_tables.sql','16_Source_Identity_and_Flock_History.sql'):
        text=(ROOT/'sql'/name).read_text(encoding='utf-8')
        for m in re.finditer(r'CREATE TABLE IF NOT EXISTS EFNS_DEV\.CORE\.(\w+)\s*\((.*?)(?:\n\);|\n\)\n)',text,re.S):
            name,body=m.groups(); key=re.search(r'PRIMARY KEY\s*\((\w+)\)',body) or re.search(r'^\s*(\w+)\s+[^\n]*PRIMARY KEY',body,re.M)
            assert key,name
            tables[name]=key[1]
    assert len(tables)==16
    n=lambda c:"NULLIF(UPPER(TRIM(TO_VARCHAR("+c+"))), '')"
    literal=lambda v:"'"+v.replace("'","''")+"'"
    statements=[]
    def add(label,meaning,body):statements.append('-- '+label+'\n-- Non-empty result: '+meaning+'\n'+body.rstrip(';')+';\n')
    add('Q00 identity','context only; STOP unless the company identity matches. Current database must be EFNS_DEV. No session context changes are made.',"SELECT CURRENT_ORGANIZATION_NAME() AS ORGANIZATION, CURRENT_ACCOUNT_NAME() AS ACCOUNT_NAME, CURRENT_ACCOUNT() AS ACCOUNT_LOCATOR, CURRENT_REGION() AS REGION, CURRENT_DATABASE() AS SESSION_DATABASE, CURRENT_ROLE() AS ROLE_NAME, 'QDCTNKN / UW19058 / CB12755 / AWS_CA_CENTRAL_1 / EFNS_DEV' AS EXPECTED_SCOPE")
    add('Q01 duplicate primary IDs - every declared CORE table','duplicate case-insensitive, trimmed identity. Check before any joined diagnostic; declared keys alone do not enforce uniqueness.','\nUNION ALL\n'.join(f"SELECT '{t}' AS TABLE_NAME, {n(k)} AS NORMALIZED_ID, COUNT(*) AS RECORDS FROM EFNS_DEV.CORE.{t} GROUP BY {n(k)} HAVING COUNT(*)>1" for t,k in sorted(tables.items())))
    add('Q01b missing primary IDs','NULL/blank identity; no repairs are implied.','\nUNION ALL\n'.join(f"SELECT '{t}' AS TABLE_NAME, TO_VARCHAR({k}) AS RECORD_ID FROM EFNS_DEV.CORE.{t} WHERE {n(k)} IS NULL" for t,k in sorted(tables.items())))
    rels=[('FLOCK','ACCOUNT_ID','ACCOUNT'),('FLOCK','FACILITY_ID','FACILITY'),('FLOCK','FACILITY_DETAIL_ID','FACILITY_DETAIL'),('FLOCK','QUOTA_ID','QUOTA_REGISTRATION'),('FLOCK_TRANSACTION','FLOCK_ID','FLOCK'),('SALMONELLA_TEST','FLOCK_ID','FLOCK'),('SALMONELLA_TEST','ACCOUNT_ID','ACCOUNT'),('QUOTA_TRANSACTION','QUOTA_ID','QUOTA_REGISTRATION'),('QUOTA_TRANSACTION','OWNER_ACCOUNT_ID','ACCOUNT'),('QUOTA_TRANSACTION','RELATED_ACCOUNT_ID','ACCOUNT'),('QUOTA_TRANSACTION','RELATED_QUOTA_ID','QUOTA_REGISTRATION'),('QUOTA_TRANSACTION','RELATED_TRANSACTION_ID','QUOTA_TRANSACTION'),('FACILITY','ACCOUNT_ID','ACCOUNT'),('FACILITY','FARM_LOCATION_ID','FARM_LOCATION'),('PRODUCTION_RECORD','PRODUCER_ACCOUNT_ID','ACCOUNT'),('PRODUCTION_RECORD','GRADER_ACCOUNT_ID','ACCOUNT'),('PRODUCTION_RECORD','FACILITY_ID','FACILITY'),('PRODUCTION_RECORD','FLOCK_ID','FLOCK'),('CONTACT','ACCOUNT_ID','ACCOUNT'),('FARM_LOCATION','ACCOUNT_ID','ACCOUNT'),('FACILITY_DETAIL','FACILITY_ID','FACILITY'),('SALMONELLA_TEST_SAMPLE','SALMONELLA_TEST_ID','SALMONELLA_TEST'),('QUOTA_REGISTRATION','ACCOUNT_ID','ACCOUNT'),('PRODUCTION_SIZE_BREAKDOWN','PRODUCTION_ID','PRODUCTION_RECORD'),('FLOCK_EVENT','FLOCK_ID','FLOCK')]
    rels.extend(('ACCOUNT',f,'ACCOUNT') for f in ('PARENT_ACCOUNT_ID','GRADING_STATION_ACCOUNT_ID','PULLET_GROWER_ACCOUNT_ID','SPENT_FOWL_PLANS_ACCOUNT_ID'))
    add('Q02 orphan references','nonempty reference has no parent. Optional NULL is allowed; text NULL remains an unresolved reference. NOT EXISTS avoids duplicate-parent fanout. Checking a semantic link does not declare a new FK.','\nUNION ALL\n'.join(f"SELECT '{c}.{f} -> {p}.{tables[p]}' AS RELATIONSHIP, TO_VARCHAR(c.{tables[c]}) AS RECORD_ID, TO_VARCHAR(c.{f}) AS REFERENCE_ID FROM EFNS_DEV.CORE.{c} c WHERE {n('c.'+f)} IS NOT NULL AND NOT EXISTS (SELECT 1 FROM EFNS_DEV.CORE.{p} p WHERE {n('p.'+tables[p])}={n('c.'+f)})" for c,f,p in rels))
    required={'FLOCK':('FLOCK_NUMBER','ACCOUNT_ID','HATCH_DATE','PERMIT_NUMBER'),'QUOTA_REGISTRATION':('ACCOUNT_ID','QUOTA_TYPE'),'FLOCK_TRANSACTION':('FLOCK_ID','TRANSACTION_TYPE','TRANSACTION_DATE','QUANTITY'),'QUOTA_TRANSACTION':('QUOTA_ID','OWNER_ACCOUNT_ID','TRANSACTION_TYPE','EFFECTIVE_DATE','QUOTA_COUNT'),'SALMONELLA_TEST':('FLOCK_ID','ACCOUNT_ID','TESTING_DATE')}
    add('Q03 missing required business fields','required field is NULL/blank. Real 0 and historical negative quantities are not missing and are NOT rejected by this check.','\nUNION ALL\n'.join(f"SELECT '{t}' AS TABLE_NAME, TO_VARCHAR({tables[t]}) AS RECORD_ID, '{f}' AS FIELD_NAME FROM EFNS_DEV.CORE.{t} WHERE {n(f)} IS NULL" for t,fields in required.items() for f in fields))
    add('Q04 multiple Delivery rows','possible duplicate or legitimate multiple Delivery: inspect source GUIDs. Matching Bird Count is only a clue, not a stock formula. Run Q01 first.',f"""WITH deliveries AS (
 SELECT {n('FLOCK_ID')} AS FLOCK_KEY, COUNT(*) AS DELIVERY_ROWS,
 COUNT(DISTINCT {n('FLOCK_TRANSACTION_ID')}) AS UNIQUE_TRANSACTION_IDS, SUM(QUANTITY) AS KNOWN_DELIVERY_SUM
 FROM EFNS_DEV.CORE.FLOCK_TRANSACTION WHERE UPPER(TRIM(TRANSACTION_TYPE))='DELIVERY'
 GROUP BY {n('FLOCK_ID')} HAVING COUNT(*)>1
)
SELECT f.FLOCK_ID, f.FLOCK_NUMBER, f.BIRD_COUNT, d.DELIVERY_ROWS, d.UNIQUE_TRANSACTION_IDS,
 d.KNOWN_DELIVERY_SUM, COALESCE(COUNT_IF(t.QUANTITY=f.BIRD_COUNT),0) AS DELIVERIES_EQUAL_BIRD_COUNT
FROM deliveries d JOIN EFNS_DEV.CORE.FLOCK f ON {n('f.FLOCK_ID')}=d.FLOCK_KEY
JOIN EFNS_DEV.CORE.FLOCK_TRANSACTION t ON {n('t.FLOCK_ID')}=d.FLOCK_KEY AND UPPER(TRIM(t.TRANSACTION_TYPE))='DELIVERY'
GROUP BY f.FLOCK_ID,f.FLOCK_NUMBER,f.BIRD_COUNT,d.DELIVERY_ROWS,d.UNIQUE_TRANSACTION_IDS,d.KNOWN_DELIVERY_SUM
ORDER BY d.DELIVERY_ROWS DESC""")
    add('Q05 owner/registration mismatch','Owner differs from registration Account, including missing Owner. Related Account is a different role. Resolve Q01 duplicates first.',f"SELECT t.QUOTA_TRANSACTION_ID,t.QUOTA_ID,t.OWNER_ACCOUNT_ID,q.ACCOUNT_ID AS REGISTRATION_ACCOUNT_ID FROM EFNS_DEV.CORE.QUOTA_TRANSACTION t JOIN EFNS_DEV.CORE.QUOTA_REGISTRATION q ON {n('t.QUOTA_ID')}={n('q.QUOTA_ID')} WHERE {n('t.OWNER_ACCOUNT_ID')} IS DISTINCT FROM {n('q.ACCOUNT_ID')}")
    const={}
    for path in ('data/constants.py','app/pages/11_Facilities.py'):
        for node in ast.parse((ROOT/path).read_text(encoding='utf-8')).body:
            if isinstance(node,ast.Assign):
                for target in node.targets:
                    if isinstance(target,ast.Name):
                        try:const[target.id]=ast.literal_eval(node.value)
                        except (ValueError,TypeError):pass
    const['QUOTA_TYPES']=const['FLOCK_QUOTA_TYPES']
    choices=[('ACCOUNT','STATUS','ACCOUNT_STATUSES'),('FARM_LOCATION','STATUS','FARM_LOCATION_STATUSES'),('FACILITY','STATUS','FACILITY_STATUSES'),('FACILITY','FACILITY_TYPE','FACILITY_TYPES'),('FACILITY_DETAIL','STATUS','FACILITY_DETAIL_STATUSES'),('FLOCK','STATUS','FLOCK_STATUSES'),('FLOCK','EGG_COLOUR','EGG_COLOURS'),('FLOCK','FLOCK_QUOTA_TYPE','FLOCK_QUOTA_TYPES'),('QUOTA_REGISTRATION','STATUS','QUOTA_STATUSES'),('QUOTA_REGISTRATION','QUOTA_TYPE','QUOTA_TYPES'),('FLOCK_TRANSACTION','TRANSACTION_TYPE','FLOCK_TRANSACTION_TYPES'),('QUOTA_TRANSACTION','TRANSACTION_TYPE','QUOTA_TRANSACTION_TYPES'),('QUOTA_TRANSACTION','QUOTA_LEASE_TYPE','QUOTA_LEASE_TYPES'),('SALMONELLA_TEST','TEST_RESULT','SALMONELLA_RESULTS')]
    add('Q06 values outside current NEW-entry choices','historical value outside current choices, NOT proof of bad data. Exact spelling differences are deliberate. Free-text fields have no invented enum.','\nUNION ALL\n'.join(f"SELECT '{t}' AS TABLE_NAME,'{f}' AS FIELD_NAME,TO_VARCHAR({f}) AS STORED_VALUE,COUNT(*) AS RECORDS FROM EFNS_DEV.CORE.{t} WHERE {n(f)} IS NOT NULL AND TO_VARCHAR({f}) NOT IN ({', '.join(literal(v) for v in const[k])}) GROUP BY {f}" for t,f,k in choices))
    add('Q07 Account names/IDs used in disposal plant or method text','name is a candidate only, not a recovered lookup GUID. Counts are distinct Flocks per field; do not sum field counts into stock.',f"""WITH disposal_text AS (
 SELECT FLOCK_ID,'DISPOSAL_PLANT' AS SOURCE_FIELD,DISPOSAL_PLANT AS STORED_TEXT FROM EFNS_DEV.CORE.FLOCK
 UNION ALL
 SELECT FLOCK_ID,'DISPOSAL_METHOD' AS SOURCE_FIELD,DISPOSAL_METHOD AS STORED_TEXT FROM EFNS_DEV.CORE.FLOCK
)
SELECT a.ACCOUNT_ID,a.ORGANIZATION_NAME,f.SOURCE_FIELD,f.STORED_TEXT,
 CASE WHEN {n('f.STORED_TEXT')}={n('a.ACCOUNT_ID')} THEN 'EXACT_ACCOUNT_ID_TEXT' ELSE 'DISPLAY_NAME_CANDIDATE_ONLY' END AS MATCH_BASIS,
 COUNT(DISTINCT {n('f.FLOCK_ID')}) AS FLOCKS
FROM disposal_text f JOIN EFNS_DEV.CORE.ACCOUNT a ON {n('f.STORED_TEXT')}={n('a.ACCOUNT_ID')} OR {n('f.STORED_TEXT')}={n('a.ORGANIZATION_NAME')}
WHERE {n('f.STORED_TEXT')} IS NOT NULL
GROUP BY a.ACCOUNT_ID,a.ORGANIZATION_NAME,f.SOURCE_FIELD,f.STORED_TEXT,MATCH_BASIS""")
    add('Q08 DEV_TEST prefix candidates','top-level value begins DEV_TEST. Inspect source/references before separately authorized cleanup. Prefix does not find every synthetic record. This query performs no deletion.','\nUNION ALL\n'.join(f"SELECT DISTINCT '{t}' AS TABLE_NAME,TO_VARCHAR(c.{k}) AS RECORD_ID,v.KEY::VARCHAR AS MARKER_FIELD,v.VALUE::VARCHAR AS MARKER_VALUE FROM EFNS_DEV.CORE.{t} c,LATERAL FLATTEN(INPUT => OBJECT_CONSTRUCT_KEEP_NULL(c.*)) v WHERE STARTSWITH(UPPER(TRIM(v.VALUE::VARCHAR)),'DEV_TEST')" for t,k in sorted(tables.items())))
    add('Q09 future/uncovered CORE tables','deployed table outside local reviewed definitions: extend diagnostics after checking metadata. No deployed inventory was queried here.',"SELECT TABLE_NAME FROM EFNS_DEV.INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='CORE' AND TABLE_TYPE='BASE TABLE' AND TABLE_NAME NOT IN ("+', '.join(literal(t) for t in sorted(tables))+')')
    return '-- OFFLINE-PREPARED ONLY; no company query executed.\n-- Use already authorized SELECT role and warehouse; run Q00 first, Q01 before joins.\n-- Local definitions: sql/02,03,12,16,18,19. Standard constraints are not enforcement evidence.\n-- Large-table scans are intentional health diagnostics; execute one labelled query at a time.\n\n'+'\n'.join(statements)

if __name__=='__main__':
    target=ROOT/'sql/review/data_health_20261030.sql'
    target.write_text(build(),encoding='utf-8')
    print('Prepared',target,'without connecting to Snowflake.')
