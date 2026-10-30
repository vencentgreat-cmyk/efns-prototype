"""Overlay an explicit reviewed scope onto the immutable live rollback copy."""
import hashlib
import json
from pathlib import Path
import shutil
import sys

import yaml

root=Path(__file__).resolve().parents[1]
base=root/'.local/continuity-20261014/deployment'
old=base/'old_app'; deploy=base/'deploy_app'
scope=(
 'data/connection.py','data/importing.py','data/constants.py','data/producer_identity.py',
 'data/production_intake.py','data/source_evidence.py','data/operational_flock_quota_import.py',
 'data/repositories/base.py','data/repositories/mock.py','data/repositories/snowflake.py','data/repositories/continuity.py',
 'app/Home.py','app/services/authorized_repository.py','app/services/report_builder.py','app/services/report_center.py',
 'app/pages/1_Production_Import.py','app/pages/2_Production_Data.py','app/pages/17_Migration_Import.py',
 'app/pages/19_Daily_Flock_Quota_Import.py','app/pages/21_Record_History.py',
 'app/pages/5_Flocks.py','app/pages/11_Facilities.py',
)
if not old.exists(): raise ValueError('Need the saved live rollback package')
if deploy.exists() and '--refresh' not in sys.argv: raise ValueError('Deployment exists; explicit --refresh is required')
if not deploy.exists(): shutil.copytree(old,deploy)
manifest=[]
for relative in scope:
 target=deploy/relative;target.parent.mkdir(parents=True,exist_ok=True)
 shutil.copy2(root/relative,target)
 manifest.append({'path':relative,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
project=yaml.safe_load((root/'snowflake.yml').read_text(encoding='utf-8'))
project['entities']['efns_dev'].pop('grants',None)
for directory in (old,deploy):
 (directory/'snowflake.yml').write_text(yaml.safe_dump(project,sort_keys=False),encoding='utf-8')
(base/'reviewed_scope.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({'reviewed_files':len(scope),'rollback':str(old),'deploy':str(deploy)}))
