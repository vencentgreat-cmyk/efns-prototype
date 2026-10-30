"""Small shared CRUD history and request boundary; uses existing history tables."""
import copy,datetime as dt,json
from functools import wraps
from decimal import Decimal
import pandas as pd
from data.repositories.base import RepositoryError,ConcurrencyError
from data.repositories.continuity import stable_id,NOW
from data.source_evidence import evidence_json
from data.producer_identity import text
from data.business_time import version_bind,same_value

ENTITIES={
 'ACCOUNT':('_accounts','upsert_account','delete_account'),
 'FARM_LOCATION':('_farm_locations','upsert_farm_location','delete_farm_location'),
 'FACILITY':('_facilities','upsert_facility','delete_facility'),
 'FACILITY_DETAIL':('_facility_details','upsert_facility_detail','delete_facility_detail'),
 'FLOCK':('_flocks','upsert_flock','delete_flock'),
 'FLOCK_TRANSACTION':('_flock_transactions','upsert_flock_transaction','delete_flock_transaction'),
 'QUOTA_REGISTRATION':('_quota_registrations','upsert_quota_registration','delete_quota_registration'),
 'QUOTA_TRANSACTION':('_quota_transactions','upsert_quota_transaction','delete_quota_transaction'),
 'SALMONELLA_TEST':('_salmonella_tests','upsert_salmonella_test','delete_salmonella_test'),
}

def actor_id(actor):return actor.get('user_id') if isinstance(actor,dict) else actor

def read_record(repo,entity,record_id,tx=None):
    from data.repositories.snowflake import MODEL
    if entity not in ENTITIES:raise RepositoryError('Unsupported record type.')
    key=MODEL[entity][0]
    if repo._is_memory:
        frame=getattr(repo,ENTITIES[entity][0]);found=frame[frame[key]==record_id]
    else:
        projection="* REPLACE (TO_CHAR(UPDATED_AT,'YYYY-MM-DD\"T\"HH24:MI:SS.FF9') AS UPDATED_AT)"
        found=(tx or repo._executor()).query(f'SELECT {projection} FROM {repo._table(entity)} WHERE {key}=%s',(record_id,))
    if len(found)>1:raise RepositoryError('Record identity is ambiguous; no write accepted.')
    return found.iloc[0].to_dict() if len(found)==1 else None

def history_audit(repo,tx,entity,record_id,request,actor,reason,kind,before,after):
    from data.repositories.continuity import stable_id
    audit=dict(AUDIT_ID=stable_id('record-audit',entity,record_id,request,kind),
        ACTOR_USER_ID=actor_id(actor),ACTOR_EMAIL=actor.get('email') if isinstance(actor,dict) else None,
        ACTION=kind if kind in ('CREATE','DELETE') else 'UPDATE',ENTITY_TYPE=entity,ENTITY_ID=record_id,
        DETAILS={'reason':reason,'request_id':request,'history_kind':kind},
        OCCURRED_AT=dt.datetime.now(dt.timezone.utc))
    if repo._is_memory:repo._review_insert(tx,'AUDIT_EVENT',audit)
    else:
        cols=list(audit);params=[evidence_json(audit[c]) if c=='DETAILS' else audit[c] for c in cols]
        slots=['PARSE_JSON(%s)' if c=='DETAILS' else '%s' for c in cols]
        if tx.execute(f"INSERT INTO {repo.database}.APP.AUDIT_EVENT ({','.join(cols)}) SELECT {','.join(slots)}",tuple(params))!=1:
            raise RepositoryError('Mandatory record audit was not saved exactly once.')

def validate_edit(repo,entity,before,changes):
    """Validate newly changed fields, never reclassify untouched historical data."""
    from data.constants import FLOCK_STATUSES,FLOCK_QUOTA_TYPES,EGG_COLOURS,QUOTA_TYPES,SALMONELLA_RESULTS,FLOCK_TRANSACTION_TYPES,QUOTA_TRANSACTION_TYPES
    from data.repositories.snowflake import MODEL,DATE_FIELDS,normalize_numeric_bind
    updated=dict(before,**changes)
    if not set(changes)<=set(MODEL[entity][1].split()):raise RepositoryError('Unknown or immutable attribute.')
    required={
      'ACCOUNT':('ORGANIZATION_NAME',),'FARM_LOCATION':('LOCATION_NAME','ACCOUNT_ID'),
      'FACILITY':('FACILITY_NAME','ACCOUNT_ID'),'FACILITY_DETAIL':('DETAIL_NAME','FACILITY_ID'),
      'FLOCK':('FLOCK_NUMBER','PERMIT_NUMBER','ACCOUNT_ID'),
      'QUOTA_REGISTRATION':('REGISTRATION_NUMBER','ACCOUNT_ID'),
      'FLOCK_TRANSACTION':('FLOCK_ID','TRANSACTION_TYPE','TRANSACTION_DATE','QUANTITY'),
      'QUOTA_TRANSACTION':('QUOTA_ID','TRANSACTION_TYPE','EFFECTIVE_DATE','QUOTA_COUNT'),
      'SALMONELLA_TEST':('FLOCK_ID','TESTING_DATE','TEST_RESULT','NUMBER_OF_SAMPLES'),
    }[entity]
    for field in set(required)&set(changes):
        if text(changes[field]) is None:raise RepositoryError(f'{field} is required when changed.')
    choices={'FLOCK':{'STATUS':FLOCK_STATUSES,'FLOCK_QUOTA_TYPE':FLOCK_QUOTA_TYPES,'EGG_COLOUR':EGG_COLOURS},
             'QUOTA_REGISTRATION':{'QUOTA_TYPE':QUOTA_TYPES},
             'FLOCK_TRANSACTION':{'TRANSACTION_TYPE':FLOCK_TRANSACTION_TYPES},
             'QUOTA_TRANSACTION':{'TRANSACTION_TYPE':QUOTA_TRANSACTION_TYPES},
             'SALMONELLA_TEST':{'TEST_RESULT':SALMONELLA_RESULTS}}.get(entity,{})
    for field,allowed in choices.items():
        if field in changes:
            from data.quota_types import supported_quota_type
            valid = supported_quota_type(changes[field]) if field in {'QUOTA_TYPE','FLOCK_QUOTA_TYPE'} else changes[field] in allowed
            if not valid:raise RepositoryError(f'{field} must use a supported choice when changed.')
    for field in set(DATE_FIELDS.get(entity,()))&set(changes):
        from data.repositories.snowflake import normalize_date_bind
        changes[field]=normalize_date_bind(changes[field],field)
    integers={'BIRD_COUNT','BIRDS_DISPOSED','NUMBER_OF_SAMPLES','QUANTITY'}
    for field in (integers|{'QUOTA_COUNT','PRICE','FACILITY_QUOTA','LATITUDE','LONGITUDE','BIRDS_HOUSED','NUMBER_OF_CAGES','HEIGHT','WIDTH','LENGTH','SQUARE_INCHES'})&set(changes):
        changes[field]=normalize_numeric_bind(changes[field],field,1,integer=field in integers)
        if field in {'BIRD_COUNT','BIRDS_DISPOSED'} and changes[field] is not None and changes[field]<0:raise RepositoryError(f'{field} cannot be negative when corrected.')
        if field=='QUANTITY' and (changes[field] is None or changes[field]<=0):raise RepositoryError('Ordinary transaction Quantity must be a positive whole number.')
        if field=='QUOTA_COUNT' and (changes[field] is None or changes[field]<=0):raise RepositoryError('Quota Count must be positive when changed in daily entry.')
        if field=='PRICE' and changes[field] is not None and changes[field]<0:raise RepositoryError('Price cannot be negative when changed in daily entry.')
        if field=='NUMBER_OF_SAMPLES' and (changes[field] is None or changes[field]<=0):raise RepositoryError('Number of Samples must be positive when changed.')
    updated=dict(before,**changes)
    parent_entities={'SPENT_FOWL_PLANS_ACCOUNT_ID':'ACCOUNT','ACCOUNT_ID':'ACCOUNT','PARENT_ACCOUNT_ID':'ACCOUNT','GRADING_STATION_ACCOUNT_ID':'ACCOUNT','PULLET_GROWER_ACCOUNT_ID':'ACCOUNT','OWNER_ACCOUNT_ID':'ACCOUNT','RELATED_ACCOUNT_ID':'ACCOUNT','FACILITY_ID':'FACILITY','FACILITY_DETAIL_ID':'FACILITY_DETAIL','FARM_LOCATION_ID':'FARM_LOCATION','FLOCK_ID':'FLOCK','QUOTA_ID':'QUOTA_REGISTRATION','RELATED_QUOTA_ID':'QUOTA_REGISTRATION','RELATED_TRANSACTION_ID':'QUOTA_TRANSACTION'}
    for field in set(changes)&set(parent_entities):
        if text(changes[field]) is not None:
            parent=read_record(repo,parent_entities[field],changes[field])
            if parent is None:raise RepositoryError(f'{field} must refer to an existing record.')
    if entity=='ACCOUNT':
        from data.account_relationships import FIELD, validate_spent_fowl_link
        if FIELD in changes: changes.update(validate_spent_fowl_link(repo, {FIELD: changes[FIELD]}))
        from data.validation import parse_optional_coordinate
        for field in {'LATITUDE','LONGITUDE'}&set(changes):changes[field]=parse_optional_coordinate(changes[field],field)
        for field in {'PARENT_ACCOUNT_ID','GRADING_STATION_ACCOUNT_ID','PULLET_GROWER_ACCOUNT_ID'}&set(changes):
            if text(changes[field])==text(before['ACCOUNT_ID']):raise RepositoryError('An Account cannot reference itself.')
    if entity=='FLOCK' and {'ACCOUNT_ID','FACILITY_DETAIL_ID','QUOTA_ID'}&set(changes):
        facility=read_record(repo,'FACILITY',updated.get('FACILITY_ID')) if updated.get('FACILITY_ID') else None
        if facility and facility['ACCOUNT_ID']!=updated['ACCOUNT_ID']:raise RepositoryError('Facility does not belong to the selected Account.')
        quota=read_record(repo,'QUOTA_REGISTRATION',updated.get('QUOTA_ID')) if updated.get('QUOTA_ID') else None
        if quota and quota['ACCOUNT_ID']!=updated['ACCOUNT_ID']:raise RepositoryError('Quota does not belong to the selected Account.')
        if quota and 'QUOTA_ID' in changes and quota.get('STATUS')!='Active':raise RepositoryError('A newly selected Quota Registration must be active; an unchanged historical link may be retained.')
        detail=read_record(repo,'FACILITY_DETAIL',updated.get('FACILITY_DETAIL_ID')) if updated.get('FACILITY_DETAIL_ID') else None
        if detail and detail['FACILITY_ID']!=updated.get('FACILITY_ID'):raise RepositoryError('Facility Detail does not belong to the Facility.')
    if entity=='FACILITY' and 'ACCOUNT_ID' in changes:repo.check_facility_ownership(updated)
    if entity=='QUOTA_TRANSACTION' and {'QUOTA_ID','OWNER_ACCOUNT_ID'}&set(changes):
        quota=read_record(repo,'QUOTA_REGISTRATION',updated['QUOTA_ID'])
        if not quota or updated.get('OWNER_ACCOUNT_ID')!=quota['ACCOUNT_ID']:raise RepositoryError('Quota Owner must match its registration Account.')
    if entity=='SALMONELLA_TEST' and 'FLOCK_ID' in changes:
        flock=read_record(repo,'FLOCK',updated['FLOCK_ID'])
        if not flock or updated['ACCOUNT_ID']!=flock['ACCOUNT_ID'] or str(updated['PERMIT_NUMBER'])!=str(flock['PERMIT_NUMBER']):raise RepositoryError('An explicitly changed Flock must use its verified Account and Permit.')
    for start,end in (('EFFECTIVE_DATE','END_DATE'),('HATCH_DATE','DISPOSAL_DATE'),('PLACEMENT_DATE','DISPOSAL_DATE'),('TESTING_DATE','DATE_RECEIVED'),('TESTING_DATE','DATE_RESULT_SENT')):
        if {start,end}&set(changes) and text(updated.get(start)) and text(updated.get(end)):
            if pd.Timestamp(updated[end])<pd.Timestamp(updated[start]):raise RepositoryError(f'{end} cannot be earlier than {start}.')
    return changes

def create_once(repo,entity,record,request_id,actor):
    from data.repositories.snowflake import MODEL
    if entity not in ENTITIES or not request_id or not actor_id(actor):raise RepositoryError('Record type, recorder and request identity are required.')
    key=MODEL[entity][0]
    if record.get(key):raise RepositoryError('Creation cannot overwrite an existing target ID.')
    values={k:v for k,v in record.items() if k!=key}
    if not set(values)<=set(MODEL[entity][1].split()):raise RepositoryError('Unknown or immutable creation field.')
    target=stable_id('record-create',entity,request_id);revision=stable_id('record-create-revision',entity,request_id)
    fingerprint=evidence_json(dict(record=values,actor=actor_id(actor)))
    with repo._continuity_transaction() as tx:
        saved=repo._history_rows('RECORD_REVISION','REVISION_ID',revision,tx)
        if not saved.empty:
            if len(saved)!=1:raise RepositoryError('Creation receipt is ambiguous.')
            after=saved.iloc[0].AFTER_DATA;after=json.loads(after) if isinstance(after,str) else after
            if after.get('_CREATE_REQUEST')!=fingerprint:raise RepositoryError('This request already created a record with different values; start a new entry.')
            if read_record(repo,entity,target,tx) is None:raise RepositoryError('Committed creation target is missing; do not retry blindly.')
            return target
        if read_record(repo,entity,target,tx):raise RepositoryError('Target already exists without a matching creation receipt.')
        getattr(repo,ENTITIES[entity][1])(dict(values,**{key:target}))
        after=read_record(repo,entity,target,tx)
        if not after:raise RepositoryError('Created record could not be verified.')
        repo._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=revision,ENTITY_TYPE=entity,ENTITY_ID=target,CHANGE_KIND='CREATE',BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor_id(actor),REASON='Explicit new record',BEFORE_DATA=None,AFTER_DATA={**after,'_CREATE_REQUEST':fingerprint}))
        history_audit(repo,tx,entity,target,request_id,actor,'Explicit new record','CREATE',None,after)
    return target

def delete_with_history(repo,entity,record_id,method,actor,request_id,reason):
    if entity not in ENTITIES:raise RepositoryError('Unsupported deletion type.')
    with repo._continuity_transaction() as tx:
        before=read_record(repo,entity,record_id,tx)
        if before is None:return False
        result=method(record_id)
        if result:
            repo._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=stable_id('record-delete',entity,record_id,request_id),ENTITY_TYPE=entity,ENTITY_ID=record_id,CHANGE_KIND='DELETE',BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor_id(actor),REASON=reason,BEFORE_DATA=before,AFTER_DATA=None))
            history_audit(repo,tx,entity,record_id,request_id,actor,reason,'DELETE',before,None)
        return result

def revise_entity(repo,entity,record_id,changes,reason,request_id,actor,business_at,expected_updated_at):
    from data.repositories.snowflake import MODEL
    from data.repositories.continuity import utc_time
    if entity not in ENTITIES or not reason or not request_id or not actor_id(actor):raise RepositoryError('A record type, reason, authenticated recorder and request identity are required.')
    if expected_updated_at is None:raise RepositoryError('Reload the record and review its version before correcting it.')
    key=MODEL[entity][0];changes=dict(changes)
    if not changes:raise RepositoryError('No changed attributes were supplied.')
    if entity=='FLOCK' and {'FACILITY_ID','DISPOSAL_DATE'}&set(changes):raise RepositoryError('Use explicit movement/end events for those changes.')
    revision=stable_id('revision',entity,record_id,request_id)
    fingerprint=evidence_json(dict(changes=changes,reason=reason,actor=actor_id(actor),business_at=business_at))
    with repo._continuity_transaction() as tx:
        saved=repo._history_rows('RECORD_REVISION','REVISION_ID',revision,tx)
        if not saved.empty:
            if len(saved)!=1:raise RepositoryError('Correction receipt is ambiguous.')
            after=saved.iloc[0].AFTER_DATA;after=json.loads(after) if isinstance(after,str) else after
            if after.get('_REVISION_REQUEST')!=fingerprint:raise RepositoryError('This correction request already has different values or reason; start a new correction.')
            return record_id
        before=read_record(repo,entity,record_id,tx)
        if before is None:raise RepositoryError('The record no longer exists.')
        if version_bind(before['UPDATED_AT'])!=version_bind(expected_updated_at):raise ConcurrencyError('Record changed after review; reload and confirm again.')
        if entity=='FLOCK_TRANSACTION':repo._guard_applied_quantity_transaction(record_id)
        changes=validate_edit(repo,entity,before,changes)
        updated=dict(before,**changes,EXPECTED_UPDATED_AT=before['UPDATED_AT'])
        if repo._is_memory:repo._upsert_frame(ENTITIES[entity][0],key,updated)
        else:repo._upsert_with_executor(tx,entity,{key:record_id,**changes,'EXPECTED_UPDATED_AT':before['UPDATED_AT']})
        after=read_record(repo,entity,record_id,tx)
        if after is None:raise RepositoryError('Corrected record could not be verified.')
        kind='QUANTITY_CORRECTION' if {'BIRD_COUNT','BIRDS_DISPOSED'}&set(changes) else 'ATTRIBUTE_CORRECTION'
        repo._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=revision,ENTITY_TYPE=entity,ENTITY_ID=record_id,CHANGE_KIND=kind,BUSINESS_AT=utc_time(business_at) if business_at else None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor_id(actor),REASON=reason,BEFORE_DATA=before,AFTER_DATA={**after,'_REVISION_REQUEST':fingerprint}))
        history_audit(repo,tx,entity,record_id,request_id,actor,reason,kind,before,after)
    return record_id

REFERENCES={
 'ACCOUNT': [('CORE',t,c) for t,c in [('ACCOUNT','SPENT_FOWL_PLANS_ACCOUNT_ID'),('ACCOUNT','PARENT_ACCOUNT_ID'),('ACCOUNT','GRADING_STATION_ACCOUNT_ID'),('ACCOUNT','PULLET_GROWER_ACCOUNT_ID'),('FARM_LOCATION','ACCOUNT_ID'),('FACILITY','ACCOUNT_ID'),('FLOCK','ACCOUNT_ID'),('CONTACT','ACCOUNT_ID'),('QUOTA_REGISTRATION','ACCOUNT_ID'),('QUOTA_TRANSACTION','OWNER_ACCOUNT_ID'),('QUOTA_TRANSACTION','RELATED_ACCOUNT_ID'),('SALMONELLA_TEST','ACCOUNT_ID'),('PRODUCTION_RECORD','PRODUCER_ACCOUNT_ID'),('PRODUCTION_RECORD','GRADER_ACCOUNT_ID')]]+[('RAW','PRODUCTION_MATCH_DECISION','ACCOUNT_ID')],
 'FARM_LOCATION':[('CORE','FACILITY','FARM_LOCATION_ID')],
 'FACILITY':[('CORE','FLOCK','FACILITY_ID'),('CORE','FACILITY_DETAIL','FACILITY_ID'),('CORE','PRODUCTION_RECORD','FACILITY_ID'),('CORE','FLOCK_EVENT','FROM_FACILITY_ID'),('CORE','FLOCK_EVENT','TO_FACILITY_ID')],
 'FACILITY_DETAIL':[('CORE','FLOCK','FACILITY_DETAIL_ID')],
 'FLOCK':[('CORE','FLOCK_TRANSACTION','FLOCK_ID'),('CORE','SALMONELLA_TEST','FLOCK_ID'),('CORE','PRODUCTION_RECORD','FLOCK_ID'),('CORE','FLOCK_EVENT','FLOCK_ID')],
 'QUOTA_REGISTRATION':[('CORE','FLOCK','QUOTA_ID'),('CORE','QUOTA_TRANSACTION','QUOTA_ID'),('CORE','QUOTA_TRANSACTION','RELATED_QUOTA_ID')],
 'QUOTA_TRANSACTION':[('CORE','QUOTA_TRANSACTION','RELATED_TRANSACTION_ID')],
 'SALMONELLA_TEST':[('CORE','SALMONELLA_TEST_SAMPLE','SALMONELLA_TEST_ID')],
}

class ReferenceConflictError(RepositoryError, ValueError):
    """A linked record blocks deletion; compatible with existing form validation."""

def guard_references(repo,entity,record_id,tx=None):
    for schema,table,column in REFERENCES.get(entity,[]):
        if repo._is_memory:
            attr={'CONTACT':'_contacts','PRODUCTION_RECORD':'_production','SALMONELLA_TEST_SAMPLE':'_salmonella_test_samples'}.get(table,ENTITIES.get(table,(None,))[0])
            if table in ('FLOCK_EVENT','PRODUCTION_MATCH_DECISION'):frame=repo._history_rows(table)
            else:frame=getattr(repo,attr,pd.DataFrame()) if attr else pd.DataFrame()
            referenced=column in frame and frame[column].eq(record_id).any()
        else:
            found=(tx or repo._executor()).query(f'SELECT 1 AS FOUND FROM {repo.database}.{schema}.{table} WHERE {column}=%s LIMIT 1',(record_id,))
            referenced=not found.empty
        if referenced:raise ReferenceConflictError(f'This {entity.replace("_", " ").title()} still has related records in {table.replace("_", " ").title()} and cannot be deleted.')

def guarded_delete(method):
    entity=next(e for e,spec in ENTITIES.items() if spec[2]==method.__name__)
    @wraps(method)
    def call(repo,record_id):
        with repo._continuity_transaction() as tx:
            guard_references(repo,entity,record_id,tx)
            return method(repo,record_id)
    return call

def locked_frame(method):
    @wraps(method)
    def call(repo,*args,**kwargs):
        with repo._continuity_lock:return method(repo,*args,**kwargs)
    return call

def serialized_write(method):
    @wraps(method)
    def call(repo,*args,**kwargs):
        with repo._continuity_transaction():return method(repo,*args,**kwargs)
    return call

def validate_parents_in_transaction(repo,entity,record,tx):
    from data.repositories.snowflake import MODEL
    for parent,references in REFERENCES.items():
        if parent not in MODEL:continue
        for schema,child,column in references:
            if child==entity and text(record.get(column)) is not None:
                key=MODEL[parent][0]
                found=tx.query(f'SELECT {key} FROM {repo._table(parent)} WHERE {key}=%s',(record[column],))
                if len(found)!=1:raise RepositoryError(f'{column} references a missing or ambiguous parent.')
