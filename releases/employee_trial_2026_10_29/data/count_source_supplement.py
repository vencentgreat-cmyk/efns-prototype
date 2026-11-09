"""Pure, immutable review plan for an explicit scope; NO database write entry."""
import hashlib
import json
import uuid
from collections import defaultdict
import pandas as pd
from data.business_time import version_bind
from data.repositories.base import RepositoryError

VERSION='COUNT_SOURCE_SUPPLEMENT_R1'
FIELD='COUNT_SOURCE_LABEL'

def missing(value):
    if value is None:return True
    if isinstance(value,str):return not value.strip()
    return bool(pd.isna(value))

def payload(value):
    return json.loads(value) if isinstance(value,str) else value

def checksum(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def identity(value):return str(value or '').strip().upper()

def preview(scope_ids,raw_rows,mappings,current_rows,files,batches,batch_id,source_file_hash):
    ids=[identity(v) for v in scope_ids]
    if not ids or len(ids)!=len(set(ids)) or any(not v for v in ids):raise RepositoryError('Explicit unique reviewed GUID scope is required.')
    indexes=[]
    for rows,key in [(raw_rows,lambda r:identity(r.get('SOURCE_ID'))),(current_rows,lambda r:identity(r.get('FLOCK_TRANSACTION_ID'))),(mappings,lambda r:(r.get('MIGRATION_BATCH_ID'),r.get('MIGRATION_RAW_ROW_ID')))]:
        index=defaultdict(list)
        for r in rows:index[key(r)].append(r)
        indexes.append(index)
    bysource,targets,byraw=indexes
    batch=[r for r in batches if r.get('MIGRATION_BATCH_ID')==batch_id]
    if len(batch)!=1 or batch[0].get('STATUS')!='COMMITTED':raise RepositoryError('Original batch is missing, ambiguous or not committed.')
    reviews=[]
    for guid in sorted(ids):
        sources=[r for r in bysource[guid] if r.get('MIGRATION_BATCH_ID')==batch_id and r.get('SOURCE_ENTITY')=='FLOCK_TRANSACTION']
        current=targets[guid];issues=[];raw=sources[0] if len(sources)==1 else {};row=current[0] if len(current)==1 else {}
        rawid=(batch_id,raw.get('MIGRATION_RAW_ROW_ID'));links=byraw[rawid];link=links[0] if len(links)==1 else {}
        if len(sources)!=1 or len(current)!=1 or len(links)!=1:issues.append('Missing or duplicated source, target or compound-identity mapping')
        if raw.get('VALIDATION_STATUS')!='READY' or link.get('STATUS')!='COMMITTED':issues.append('Source/mapping is not committed READY')
        if any(identity(v)!=guid for v in [raw.get('TARGET_ID'),link.get('SOURCE_ID'),link.get('TARGET_ID')]) or link.get('SOURCE_ENTITY')!='FLOCK_TRANSACTION':issues.append('Source/mapping GUID identity mismatch')
        filematches=[f for f in files if (f.get('MIGRATION_BATCH_ID'),f.get('SOURCE_FILENAME'),f.get('SOURCE_ENTITY'))==(batch_id,raw.get('SOURCE_FILENAME'),'FLOCK_TRANSACTION')]
        if len(filematches)!=1 or filematches[0].get('FILE_HASH')!=source_file_hash:issues.append('Original file identity/hash mismatch')
        data=payload(raw.get('RAW_DATA')) or {};values={str(k).lower():v for k,v in data.items()}
        label=values.get('efc_flockcounttype_displayname')
        # Source labels are evidence, not an enum we invent. Never turn an unknown code into a label.
        if label is None or str(label).strip().casefold() in {'','null','none','nan'}:issues.append('Original display label not supplied; do not infer from the numeric code')
        current_value=row.get(FIELD)
        if not missing(current_value):disposition='KEEP_EXISTING'
        elif issues:disposition='HOLD'
        elif missing(row.get('UPDATED_AT')):disposition='HOLD';issues.append('Missing current FF9 version')
        else:disposition='READY_FOR_REVIEW'
        proposal=dict(supplement_version=VERSION,original_batch=batch_id,raw_row_id=rawid[1],source_guid=guid,target_guid=guid,source_filename=raw.get('SOURCE_FILENAME'),source_row_number=raw.get('SOURCE_ROW_NUMBER'),source_file_sha256=source_file_hash,raw_sha256=checksum(data),normalized_sha256=checksum(payload(raw.get('NORMALIZED_DATA'))),current_row_sha256=checksum(row),expected_updated_at_ff9=version_bind(row.get('UPDATED_AT')),expected_old_value=None if missing(current_value) else current_value,proposed_value=label)
        reviews.append(dict(proposal,current_value=None if missing(current_value) else current_value,disposition=disposition,issues=issues,review_token=checksum(proposal)))
    digest=checksum([r['review_token'] for r in reviews]);operation=str(uuid.uuid5(uuid.NAMESPACE_URL,VERSION+':'+digest))
    for r in reviews:r['operation_id']=operation;r['request_id']=str(uuid.uuid5(uuid.NAMESPACE_URL,operation+':'+r['target_guid']))
    return {'supplement_version':VERSION,'review_set_sha256':digest,'operation_id':operation,'records':reviews}

def verify_reviewed_plan(plan,current_plan):
    """No implicit rebasing: stale source/version/content or altered token is a conflict."""
    for p in [plan,current_plan]:
        for row in p['records']:
            fields={k:v for k,v in row.items() if k not in {'current_value','disposition','issues','review_token','operation_id','request_id'}}
            if checksum(fields)!=row['review_token']:raise RepositoryError('Review content changed.')
        if checksum([r['review_token'] for r in p['records']])!=p['review_set_sha256']:raise RepositoryError('Review set changed.')
    if plan['review_set_sha256']!=current_plan['review_set_sha256']:raise RepositoryError('Source or current FF9 version changed; stop for review, do not rebase.')
    if any(r['disposition']!='READY_FOR_REVIEW' for r in current_plan['records']):raise RepositoryError('This reviewed scope is not wholly eligible.')
    return True

def chunks(plan,size=500):
    if not isinstance(size,int) or not 1<=size<=500:raise RepositoryError('Review chunks must contain 1–500 rows.')
    return [plan['records'][i:i+size] for i in range(0,len(plan['records']),size)]
