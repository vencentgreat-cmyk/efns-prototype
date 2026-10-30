"""Restricted writer adapter around the deployed SnowparkExecutor, not a new writer."""
import json
import pandas as pd
from data.connection import SnowparkExecutor
from data.business_time import advance_version_sql,version_bind
from data.repositories.snowflake import UTC_NOW_NTZ
from data.repositories.base import RepositoryError
from core import FIELD,identities,reason_for,digest


class RestrictedExecutor(SnowparkExecutor):
    def __init__(self,session,records,review_hash,actor):
        super().__init__(session)
        self.allowed={r['source_account_guid']:r for r in records}
        self.review_hash=review_hash;self.actor=actor
        self.calls=[];self.control=[]

    def _collect(self,sql,params=None):
        if sql not in {'BEGIN','COMMIT','ROLLBACK'}:
            if getattr(self,'_approved_statement',None)!=(sql,tuple(params or ())):
                raise RepositoryError('Unexpected transaction control SQL.')
            return super()._collect(sql,params)
        self.control.append({'sql':sql,'outcome':'ATTEMPTED'})
        try:
            result=super()._collect(sql,params)
            self.control[-1]['outcome']='SUCCESS'
            return result
        except Exception:
            self.control[-1]['outcome']='ERROR';raise

    def execute_bounded(self,sql,params=None,timeout_seconds=30):
        expected="UPDATE EFNS_DEV.RAW.INTAKE_LOCK SET VERSION=VERSION+1 WHERE LOCK_ID='continuity'"
        if sql!=expected or timeout_seconds!=30 or params not in (None,(),[]):
            raise RepositoryError('Only the approved single intake lock statement is bounded.')
        self.calls.append({'kind':'LOCK'})
        return super().execute_bounded(sql,params,timeout_seconds)

    def execute(self,sql,params=None):
        params=tuple(params or ())
        expected=f'UPDATE EFNS_DEV.CORE.ACCOUNT SET {FIELD} = %s, UPDATED_AT = {advance_version_sql(UTC_NOW_NTZ)} WHERE ACCOUNT_ID = %s AND UPDATED_AT = %s'
        if sql==expected and len(params)==3:
            target,account,version=params
            row=self.allowed.get(account)
            if row is None or target!=row['proposed_lookup_id'] or version_bind(version)!=version_bind(row['expected_updated_at_ff9']):
                raise RepositoryError('Unapproved Account target, value or version.')
            kind='ACCOUNT'
        elif sql.startswith('INSERT INTO EFNS_DEV.APP.RECORD_REVISION '):
            if len(params)!=10:raise RepositoryError('Unexpected revision payload.')
            row=self.allowed.get(params[2])
            if row is None or params[0]!=identities(row)[0] or params[1]!='ACCOUNT' or params[3]!='ATTRIBUTE_CORRECTION' or params[4] is not None or params[6]!=self.actor.user_id or params[7]!=reason_for(row,self.review_hash):
                raise RepositoryError('Unapproved revision identity or recorder.')
            kind='REVISION'
        elif sql.startswith('INSERT INTO EFNS_DEV.APP.AUDIT_EVENT '):
            if len(params)!=8:raise RepositoryError('Unexpected audit payload.')
            row=self.allowed.get(params[5]);details=json.loads(params[6])
            if row is None or params[0]!=identities(row)[1] or params[1]!=self.actor.user_id or params[2]!=self.actor.email or params[3:5]!=('UPDATE','ACCOUNT') or details.get('request_id')!=row['proposed_request_id'] or details.get('reason')!=reason_for(row,self.review_hash):
                raise RepositoryError('Unapproved audit identity or recorder.')
            kind='AUDIT'
        else:
            raise RepositoryError('SQL write is outside the approved supplement scope.')
        self.calls.append({'kind':kind})
        self._approved_statement=(sql,params)
        try:return super().execute(sql,params)
        finally:self._approved_statement=None


def plain(value):
    from data.source_evidence import evidence_json
    return json.loads(evidence_json(value))


def read_snapshot(ex,rows,batch):
    rawids=[r['raw_row_id'] for r in rows];marks=','.join(['%s']*26)
    revision_ids=[identities(r)[0] for r in rows];audit_ids=[identities(r)[1] for r in rows]
    requests=[r['proposed_request_id'] for r in rows]
    def q(sql,params=()):return plain(ex.query(sql,params).to_dict('records'))
    return dict(
        accounts=q("SELECT * REPLACE (TO_CHAR(UPDATED_AT,'YYYY-MM-DD\"T\"HH24:MI:SS.FF9') AS UPDATED_AT,TO_CHAR(CREATED_AT,'YYYY-MM-DD\"T\"HH24:MI:SS.FF9') AS CREATED_AT) FROM EFNS_DEV.CORE.ACCOUNT ORDER BY ACCOUNT_ID"),
        raw=q('SELECT * FROM EFNS_DEV.RAW.MIGRATION_RAW_ROW WHERE MIGRATION_BATCH_ID=%s AND MIGRATION_RAW_ROW_ID IN ('+marks+') ORDER BY MIGRATION_RAW_ROW_ID',(batch,*rawids)),
        mappings=q('SELECT * FROM EFNS_DEV.RAW.MIGRATION_ID_MAP WHERE MIGRATION_BATCH_ID=%s AND MIGRATION_RAW_ROW_ID IN ('+marks+') ORDER BY MIGRATION_RAW_ROW_ID',(batch,*rawids)),
        batch=q('SELECT * FROM EFNS_DEV.RAW.MIGRATION_BATCH WHERE MIGRATION_BATCH_ID=%s',(batch,)),
        revisions=q("SELECT * FROM EFNS_DEV.APP.RECORD_REVISION WHERE REVISION_ID IN ("+marks+") OR (ENTITY_TYPE='ACCOUNT' AND REASON LIKE %s) ORDER BY REVISION_ID",(*revision_ids,'%'+rows[0]['review_set']+'%')),
        audits=q("SELECT * FROM EFNS_DEV.APP.AUDIT_EVENT WHERE AUDIT_ID IN ("+marks+") OR (ENTITY_TYPE='ACCOUNT' AND DETAILS:request_id::STRING IN ("+marks+')) ORDER BY AUDIT_ID',(*audit_ids,*requests)))


def unique(rows,key):
    result={key(r):r for r in rows}
    if len(result)!=len(rows):raise RepositoryError('Duplicate identity; count-only verification is forbidden.')
    return result


def as_object(v):return json.loads(v) if isinstance(v,str) else v


def check_before(state,rows,batch):
    accounts=unique(state['accounts'],lambda r:r['ACCOUNT_ID'])
    raw=unique(state['raw'],lambda r:(r['MIGRATION_BATCH_ID'],r['MIGRATION_RAW_ROW_ID']))
    maps=unique(state['mappings'],lambda r:(r['MIGRATION_BATCH_ID'],r['MIGRATION_RAW_ROW_ID']))
    if len(raw)!=26 or len(maps)!=26 or len(state['batch'])!=1 or state['batch'][0]['STATUS']!='COMMITTED':
        raise RepositoryError('Original source/mapping/batch is incomplete or not committed.')
    issues=[]
    for row in rows:
        p=row['proposal'];identity=(batch,row['raw_row_id']);source=raw.get(identity);mapping=maps.get(identity)
        account=accounts.get(row['source_account_guid']);target=accounts.get(row['proposed_lookup_id'])
        if not source or not mapping or not account or not target:issues.append(row['source_account_guid']+': missing identity');continue
        data=as_object(source['RAW_DATA']);normal=as_object(source['NORMALIZED_DATA'])
        if digest(data)!=p['raw_payload_sha256'] or digest(normal)!=p['normalized_payload_sha256']:issues.append(row['source_account_guid']+': immutable source hash conflict')
        if source['SOURCE_ENTITY']!='ACCOUNT' or source['VALIDATION_STATUS']!='READY' or source['SOURCE_FILENAME']!=p['source_filename'] or int(source['SOURCE_ROW_NUMBER'])!=p['source_row_number']:issues.append(row['source_account_guid']+': original row identity/status conflict')
        if str(data.get('EFNS_SPENTFOWLPLANS','')).upper()!=row['proposed_lookup_id'] or source['SOURCE_ID'].upper()!=row['source_account_guid'] or source['TARGET_ID'].upper()!=row['source_account_guid'] or mapping['TARGET_ID'].upper()!=row['source_account_guid'] or mapping['STATUS']!=p['expected_mapping_status']:issues.append(row['source_account_guid']+': GUID/mapping conflict')
        if account.get(FIELD)!=p['expected_old_link'] or version_bind(account['UPDATED_AT'])!=version_bind(p['expected_updated_at_ff9']):issues.append(row['source_account_guid']+': current source value/version conflict')
        if version_bind(target['UPDATED_AT'])!=version_bind(p['target_updated_at_ff9']):issues.append(row['source_account_guid']+': target version conflict')
    if issues:
        exc=RepositoryError('Approved plan conflicts; no version refresh permitted. '+ '; '.join(issues))
        exc.conflicts=issues;raise exc
    if state['revisions'] or state['audits']:raise RepositoryError('Existing operation evidence must be verified as a whole before any write.')
    return state


def equivalent(key,left,right):
    if left is None or right is None:return left is None and right is None
    if key.endswith('_AT') or key.endswith('_DATE'):
        return pd.Timestamp(left)==pd.Timestamp(right)
    return left==right


def check_after(before,after,rows,review_hash,actor):
    first=unique(before['accounts'],lambda r:r['ACCOUNT_ID']);last=unique(after['accounts'],lambda r:r['ACCOUNT_ID'])
    if first.keys()!=last.keys():raise RepositoryError('Account identities changed.')
    selected={r['source_account_guid']:r for r in rows}
    for aid,old in first.items():
        current=last[aid]
        for key in old.keys()|current.keys():
            if aid in selected and key in {FIELD,'UPDATED_AT'}:continue
            if not equivalent(key,old.get(key),current.get(key)):raise RepositoryError('An unapproved Account attribute changed: '+aid+':'+key)
        if aid in selected:
            if current.get(FIELD)!=selected[aid]['proposed_lookup_id'] or pd.Timestamp(current['UPDATED_AT'])<=pd.Timestamp(old['UPDATED_AT']):raise RepositoryError('Per-GUID target or strictly increasing version failed.')
    for key in ['raw','mappings','batch']:
        if digest(before[key])!=digest(after[key]):raise RepositoryError('Original source tracking changed: '+key)
    revisions=unique(after['revisions'],lambda r:r['REVISION_ID']);audits=unique(after['audits'],lambda r:r['AUDIT_ID'])
    if len(revisions)!=26 or len(audits)!=26:raise RepositoryError('Expected exactly 26 unique revisions and audits.')
    for row in rows:
        aid=row['source_account_guid'];rid,auditid=identities(row)
        revision=revisions.get(rid);audit=audits.get(auditid)
        if revision is None or audit is None:raise RepositoryError('Missing corresponding per-GUID revision/audit.')
        expected_reason=reason_for(row,review_hash)
        if revision['ENTITY_ID']!=aid or revision['ENTITY_TYPE']!='ACCOUNT' or revision['RECORDED_BY']!=actor.user_id or revision['REASON']!=expected_reason or revision['CHANGE_KIND']!='ATTRIBUTE_CORRECTION':raise RepositoryError('Revision scope/actor/reason mismatch.')
        old=as_object(revision['BEFORE_DATA']);new=as_object(revision['AFTER_DATA'])
        for key in first[aid]:
            if not equivalent(key,first[aid].get(key),old.get(key)) or not equivalent(key,last[aid].get(key),new.get(key)):raise RepositoryError('Revision before/after does not match the verified Account: '+key)
        from data.source_evidence import evidence_json
        expected=evidence_json(dict(changes={FIELD:row['proposed_lookup_id']},reason=expected_reason,actor=actor.user_id,business_at=None))
        if new.get('_REVISION_REQUEST')!=expected:raise RepositoryError('Revision replay fingerprint differs.')
        details=as_object(audit['DETAILS'])
        if audit['ENTITY_ID']!=aid or audit['ENTITY_TYPE']!='ACCOUNT' or audit['ACTION']!='UPDATE' or audit['ACTOR_USER_ID']!=actor.user_id or audit['ACTOR_EMAIL']!=actor.email or details['request_id']!=row['proposed_request_id'] or details['reason']!=expected_reason:raise RepositoryError('Audit scope/actor/request mismatch.')
    return {'verified_accounts':26,'unique_revisions':26,'unique_audits':26,'other_account_attributes_unchanged':True,'original_source_unchanged':True}
