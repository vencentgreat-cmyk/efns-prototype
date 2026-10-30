"""Prepare a file-preserving official Snowsight upload route; no network/DDL."""
from __future__ import annotations

from collections import defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / '.local/company-20261019'


def prepare(bundle=BUNDLE):
    bundle = Path(bundle)
    manifest = json.loads((bundle / 'application_manifest.json').read_text(encoding='utf-8'))
    groups = defaultdict(list)
    files = []
    for row in manifest:
        name = row['path']
        path = bundle / 'app' / name
        if not re.fullmatch(r'[A-Za-z0-9_./-]+', name) or '..' in Path(name).parts:
            raise ValueError('Unsafe upload path')
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('Package differs from its saved manifest: ' + name)
        files.append({**row, 'bytes': len(data)})
        groups[Path(name).parent.as_posix()].append(Path(name).name)
    release = 'release_20261019_' + hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()[:12]
    destination = bundle / 'snowsight'
    destination.mkdir(exist_ok=True)
    rows = []
    for number, (folder, names) in enumerate(sorted(groups.items()), 1):
        suffix = '' if folder == '.' else '/' + folder
        rows.append({'group': number, 'local_folder': str(bundle / 'app' / folder),
                     'stage_path': release + suffix, 'file_count': len(names),
                     'files': '; '.join(sorted(names))})
    with (destination / 'Upload_Groups.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    (destination / 'File_Manifest.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    expected = ',\n'.join(f" ('{row['path']}', {row['bytes']})" for row in files)
    sql = f"""-- Application creation only. No initialization DDL or business rows.
-- Upload the extracted files in Upload_Groups.csv first, NOT the ZIP itself.
USE ROLE EFNS_DEV_DEPLOYER;
USE SECONDARY ROLES NONE;
USE WAREHOUSE EFNS_DEV_WH;
USE DATABASE EFNS_DEV;
USE SCHEMA APP;
SELECT CURRENT_ORGANIZATION_NAME(),CURRENT_ACCOUNT_NAME(),CURRENT_ACCOUNT(),CURRENT_REGION(),CURRENT_ROLE(),CURRENT_DATABASE();
EXECUTE IMMEDIATE $$
DECLARE
 wrong_target EXCEPTION (-20001,'Company account/database/role mismatch');
 existing_app EXCEPTION (-20002,'Application already exists; stop and preserve its source');
 wrong_files EXCEPTION (-20003,'Uploaded paths or sizes differ; inspect Upload_Groups.csv, do not create app');
 n NUMBER;
BEGIN
 IF (CURRENT_ORGANIZATION_NAME()<>'QDCTNKN' OR CURRENT_ACCOUNT_NAME()<>'UW19058'
     OR CURRENT_ACCOUNT()<>'CB12755' OR CURRENT_REGION()<>'AWS_CA_CENTRAL_1'
     OR CURRENT_DATABASE()<>'EFNS_DEV' OR CURRENT_ROLE()<>'EFNS_DEV_DEPLOYER') THEN RAISE wrong_target; END IF;
 SHOW STREAMLITS LIKE 'EFNS_INTERNAL_APP' IN SCHEMA EFNS_DEV.APP;
 SELECT COUNT(*) INTO :n FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()));
 IF (n<>0) THEN RAISE existing_app; END IF;
 LIST @EFNS_DEV.APP.EFNS_STREAMLIT_STAGE/{release}/;
 WITH uploaded AS (
   SELECT REGEXP_REPLACE("name", '^.*/{release}/', '') AS path, "size" AS bytes
   FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))
 ), expected AS (SELECT column1 AS path,column2 AS bytes FROM VALUES
{expected}
 )
 SELECT COUNT(*) INTO :n FROM expected e FULL OUTER JOIN uploaded u ON e.path=u.path
 WHERE e.path IS NULL OR u.path IS NULL OR e.bytes<>u.bytes;
 IF (n<>0) THEN RAISE wrong_files; END IF;
 EXECUTE IMMEDIATE 'CREATE STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP FROM ''@EFNS_DEV.APP.EFNS_STREAMLIT_STAGE/{release}/'' MAIN_FILE=''streamlit_app.py'' QUERY_WAREHOUSE=EFNS_DEV_WH RUNTIME_NAME=''SYSTEM$WAREHOUSE_RUNTIME'' TITLE=''EFNS Internal Data System''';
 EXECUTE IMMEDIATE 'ALTER STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP ADD LIVE VERSION FROM LAST';
END;
$$;
SHOW STREAMLITS LIKE 'EFNS_INTERNAL_APP' IN SCHEMA EFNS_DEV.APP;
DESCRIBE STREAMLIT EFNS_DEV.APP.EFNS_INTERNAL_APP;
-- Next run ONLY sql/08_post_deploy_grants.sql, then open the app as its real viewer.
-- Path/size verification is not remote byte-hash verification or browser acceptance.
"""
    (destination / '03_Create_Application_After_Web_Upload.sql').write_text(sql, encoding='utf-8')
    print(json.dumps({'output': str(destination), 'release_path': release,
                      'upload_groups': len(rows), 'files': len(files), 'remote_executed': False}))
    return destination


if __name__ == '__main__':
    prepare()
