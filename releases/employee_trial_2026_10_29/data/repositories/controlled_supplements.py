"""Two restricted supplements using existing intake transaction/evidence structures."""
from contextlib import contextmanager
import copy,datetime as dt,io,json,uuid
from decimal import Decimal
import pandas as pd
from data.repositories.base import RepositoryError,ConcurrencyError
from data.repositories.continuity import stable_id
from data.business_time import version_bind,advance_version_sql
from data.source_evidence import evidence_json
from data.controlled_primitives import digest,bytehash,unique,batches

def validate_case(plan):
    from data.controlled_case import validate_case as call
    return call(plan)
def build_case(blobs,policy):
    from data.controlled_case import build_case as call
    return call(blobs,policy)

NOW="CONVERT_TIMEZONE('UTC',CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"
ROUTE='OCT29_HISTORY_SUPPLEMENT'
TABLES={'FLOCK':('CORE','FLOCK_ID','_flocks'),'FLOCK_TRANSACTION':('CORE','FLOCK_TRANSACTION_ID','_flock_transactions'),'ACCOUNT':('CORE','ACCOUNT_ID','_accounts'),'FACILITY':('CORE','FACILITY_ID','_facilities'),'RECORD_REVISION':('APP','REVISION_ID',None),'AUDIT_EVENT':('APP','AUDIT_ID','_migration_review_audit'),'SOURCE_FILE':('RAW','SOURCE_FILE_ID',None),'IMPORT_BATCH':('RAW','IMPORT_ID','_import_batches'),'IMPORT_RAW_ROW':('RAW','RAW_ROW_ID','_raw_rows')}
JSON_FIELDS={'RAW_DATA','VALIDATION_MESSAGES','DETAILS','BEFORE_DATA','AFTER_DATA'}
TIME_FIELDS={'CREATED_AT','UPDATED_AT','RECORDED_AT','OCCURRED_AT','UPLOADED_AT','UPLOAD_TIMESTAMP'}

def value(v):return json.loads(v) if isinstance(v,str) else v
def gid(v):return str(v or '').strip().upper()
def canonical(row):return json.loads(evidence_json(row))
def equal(field,a,b):
    if a is None or b is None:return a is None and b is None
    if field.endswith('_AT') or field=='UPLOAD_TIMESTAMP':return version_bind(a)==version_bind(b)
    if field.endswith('_DATE') or field=='EST_DISPOSAL':return pd.Timestamp(a).date()==pd.Timestamp(b).date()
    if field in {'QUANTITY','BIRD_COUNT','BIRDS_DISPOSED'}:return Decimal(str(a))==Decimal(str(b))
    return a==b
def unchanged(old,new,except_fields=()):
    return all(equal(k,old.get(k),new.get(k)) for k in old.keys()|new.keys() if k not in except_fields)
def progress(callback,state,done,total):
    if callback:
        try:callback(dict(state=state,processed=done,total=total,committed=state=='COMMITTED'))
        except Exception:pass # Notification cannot turn a committed write into a reported failure.

class ControlledSupplementRepository:
    @staticmethod
    def _cs_count_identity(plan):
        from data.count_source_supplement import VERSION,verify_reviewed_plan
        verify_reviewed_plan(plan,plan)
        expected=str(uuid.uuid5(uuid.NAMESPACE_URL,VERSION+':'+plan['review_set_sha256']))
        if plan['operation_id']!=expected or any(r['operation_id']!=expected for r in plan['records']):raise RepositoryError('Reviewed count operation identity changed.')
    def _cs_original_batch(self,plan,tx=None):
        id=plan['policy']['original_batch']
        rows=[r for r in self._migration_batches if r['MIGRATION_BATCH_ID']==id] if self._is_memory else (tx or self._executor()).query(f'SELECT MIGRATION_BATCH_ID,STATUS FROM {self.database}.RAW.MIGRATION_BATCH WHERE MIGRATION_BATCH_ID=%s',(id,)).to_dict('records')
        if len(rows)!=1 or rows[0]['STATUS']!='COMMITTED':raise RepositoryError('Exactly one committed original migration batch is required; never modify it.')
    def _cs_company(self,tx=None):
        if self._is_memory:return dict(ORG='QDCTNKN',ACCOUNT_NAME='UW19058',LOCATOR='CB12755',REGION='AWS_CA_CENTRAL_1',DB='EFNS_DEV',SESSION_ID='mock-'+str(id(self)),evidence='MOCK_ONLY')
        frame=(tx or self._executor()).query('SELECT CURRENT_ORGANIZATION_NAME() ORG,CURRENT_ACCOUNT_NAME() ACCOUNT_NAME,CURRENT_ACCOUNT() LOCATOR,CURRENT_REGION() REGION,CURRENT_DATABASE() DB,CURRENT_SESSION() SESSION_ID')
        if len(frame)!=1:raise RepositoryError('Company identity is ambiguous.')
        identity=frame.iloc[0].to_dict()
        if self.database!='EFNS_DEV' or tuple(identity[k] for k in ['ORG','ACCOUNT_NAME','LOCATOR','REGION','DB'])!=('QDCTNKN','UW19058','CB12755','AWS_CA_CENTRAL_1','EFNS_DEV'):raise RepositoryError('Restricted to verified company DEV.')
        return identity

    def _cs_read(self,table,ids=None,tx=None,import_id=None):
        schema,key,attribute=TABLES[table]
        if self._is_memory:
            records=self._continuity_rows[table] if attribute is None else getattr(self,attribute,[])
            if isinstance(records,pd.DataFrame):records=records.to_dict('records')
            wanted={gid(i) for i in ids} if ids is not None else None
            return [canonical(r) for r in records if (wanted is None or gid(r.get(key)) in wanted) and (import_id is None or r.get('IMPORT_ID')==import_id)]
        projection="* REPLACE (TO_CHAR(UPDATED_AT,'YYYY-MM-DD\"T\"HH24:MI:SS.FF9') AS UPDATED_AT,TO_CHAR(CREATED_AT,'YYYY-MM-DD\"T\"HH24:MI:SS.FF9') AS CREATED_AT)" if schema=='CORE' else '*'
        sql=f'SELECT {projection} FROM {self.database}.{schema}.{table}';conditions=[];params=[]
        if ids is not None:
            if not ids:return []
            conditions.append(f'UPPER({key}) IN (SELECT UPPER(VALUE::VARCHAR) FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))');params.append(evidence_json(list(ids)))
        if import_id is not None:conditions.append('IMPORT_ID=%s');params.append(import_id)
        if conditions:sql+=' WHERE '+' AND '.join(conditions)
        return [canonical(r) for r in (tx or self._executor()).query(sql,tuple(params)).to_dict('records')]

    def _cs_insert(self,tx,table,records):
        if not records:return
        schema,key,attribute=TABLES[table]
        from data.repositories.snowflake import MODEL
        allowed=set(MODEL[table][1].split())|{key} if schema=='CORE' else {
            'RECORD_REVISION':set('REVISION_ID ENTITY_TYPE ENTITY_ID CHANGE_KIND BUSINESS_AT RECORDED_AT RECORDED_BY REASON BEFORE_DATA AFTER_DATA'.split()),
            'AUDIT_EVENT':set('AUDIT_ID ACTOR_USER_ID ACTOR_EMAIL ACTION ENTITY_TYPE ENTITY_ID DETAILS OCCURRED_AT'.split()),
            'SOURCE_FILE':set('SOURCE_FILE_ID ORIGINAL_FILENAME FILE_HASH FILE_SIZE_BYTES STAGE_PATH IMPORT_ROUTE PARSE_STATUS PARSE_ERROR UPLOADED_BY UPLOADED_AT'.split()),
            'IMPORT_BATCH':set('IMPORT_ID FILENAME SOURCE FILE_HASH FILE_SIZE_BYTES SOURCE_RECORD_COUNT ROW_COUNT ERROR_COUNT STATUS NOTES SOURCE_FILE_ID UPLOAD_TIMESTAMP CREATED_AT UPDATED_AT'.split()),
            'IMPORT_RAW_ROW':set('RAW_ROW_ID IMPORT_ID SOURCE_ROW_NUMBER RAW_DATA VALIDATION_STATUS MATCH_STATUS VALIDATION_MESSAGES SOURCE_FILE_ID TARGET_ENTITY TARGET_ID CREATED_AT UPDATED_AT'.split())}[table]
        fields=sorted(set().union(*(r.keys() for r in records)))
        if not set(fields)<=allowed|TIME_FIELDS:raise RepositoryError('Unapproved supplemental write columns.')
        times={'CREATED_AT','UPDATED_AT'} if schema=='CORE' or table=='IMPORT_RAW_ROW' else {'RECORDED_AT'} if table=='RECORD_REVISION' else {'OCCURRED_AT'} if table=='AUDIT_EVENT' else {'UPLOADED_AT'} if table=='SOURCE_FILE' else {'CREATED_AT','UPDATED_AT','UPLOAD_TIMESTAMP'}
        fields=sorted(set(fields)|times)
        for part in batches(records):
            if self._is_memory:
                stamp=pd.Timestamp.now(tz='UTC').tz_localize(None).isoformat();new=[dict(canonical(r),**{f:stamp for f in times}) for r in part]
                if schema=='CORE':setattr(self,attribute,pd.concat([getattr(self,attribute),pd.DataFrame(new)],ignore_index=True))
                elif attribute is None:self._continuity_rows[table].extend(copy.deepcopy(new))
                else:
                    if not hasattr(self,attribute):setattr(self,attribute,[])
                    getattr(self,attribute).extend(copy.deepcopy(new))
                continue
            def expression(f):
                if f in times:return NOW
                # A CREATE has no old record: preserve JSON null inside the non-null VARIANT snapshot.
                if f in {'BEFORE_DATA','AFTER_DATA'}:return f'v.VALUE:{f}'
                if f in JSON_FIELDS:return f'IFF(IS_NULL_VALUE(v.VALUE:{f}),NULL,v.VALUE:{f})'
                typ='TIMESTAMP_NTZ' if f in TIME_FIELDS or f=='BUSINESS_AT' else 'DATE' if f.endswith('_DATE') or f=='EST_DISPOSAL' else 'NUMBER(38,6)' if f=='QUANTITY' else 'NUMBER(38,0)' if f in {'BIRD_COUNT','BIRDS_DISPOSED','SOURCE_ROW_NUMBER','FILE_SIZE_BYTES','SOURCE_RECORD_COUNT','ROW_COUNT','ERROR_COUNT'} else 'BOOLEAN' if f=='CREATE_DELIVERY_TRANSACTION' else 'VARCHAR'
                return f'IFF(IS_NULL_VALUE(v.VALUE:{f}),NULL,v.VALUE:{f}::{typ})'
            sql=f'/*cs:insert:{table}*/ INSERT INTO {self.database}.{schema}.{table} ({",".join(fields)}) SELECT '+','.join(expression(f) for f in fields)+' FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))) v'
            if tx.execute(sql,(evidence_json(part),))!=len(part):raise RepositoryError('Supplement batch insert count mismatch; nothing may commit.')

    def _cs_receipt(self,operation,tx=None):
        rows=self._cs_read('AUDIT_EVENT',[stable_id('cs-receipt',operation)],tx)
        if len(rows)>1:raise RepositoryError('Operation receipt is duplicated.')
        return value(rows[0]['DETAILS']) if rows else None

    def _cs_history(self,tx,operation,kind,items,actor):
        revisions=[];audits=[]
        for item in items:
            entity=item['entity'];id=item['guid'];source=item['source'];after=item['after'];before=item['before'];reason=evidence_json(dict(operation=operation,kind=kind,source=source))
            if len(reason)>1900:reason=evidence_json(dict(operation=operation,kind=kind,source_sha256=digest(source)))
            meta={'operation':operation,'kind':kind,'source':source,'after_sha256':digest(after)}
            revisions.append(dict(REVISION_ID=stable_id('cs-revision',operation,entity,id),ENTITY_TYPE=entity,ENTITY_ID=id,CHANGE_KIND='ATTRIBUTE_CORRECTION' if kind=='COUNT_LABEL' else 'CREATE',BUSINESS_AT=None,RECORDED_BY=actor['user_id'],REASON=reason,BEFORE_DATA=before,AFTER_DATA=dict(after,_CONTROLLED_SUPPLEMENT=meta)))
            audits.append(dict(AUDIT_ID=stable_id('cs-audit',operation,entity,id),ACTOR_USER_ID=actor['user_id'],ACTOR_EMAIL=actor['email'],ACTION='UPDATE' if kind=='COUNT_LABEL' else 'CREATE',ENTITY_TYPE=entity,ENTITY_ID=id,DETAILS=dict(operation=operation,kind=kind,source=source,after_sha256=digest(after))))
        self._cs_insert(tx,'RECORD_REVISION',revisions);self._cs_insert(tx,'AUDIT_EVENT',audits)

    def _cs_finish(self,tx,operation,kind,seal,ids,actor,session):
        entity='FLOCK' if kind=='INCREMENT_A' else 'FLOCK_TRANSACTION'
        history=self._cs_read('RECORD_REVISION',[stable_id('cs-revision',operation,entity,id) for id in ids],tx)
        history=sorted(history,key=lambda r:r['REVISION_ID'])
        history_hash=digest([{k:r[k] for k in ['REVISION_ID','ENTITY_TYPE','ENTITY_ID','CHANGE_KIND','RECORDED_BY','REASON','BEFORE_DATA','AFTER_DATA']} for r in history])
        details=dict(operation=operation,kind=kind,seal=seal,count=len(ids),scope_sha256=digest(sorted(ids)),history_sha256=history_hash,session_id=str(session['SESSION_ID']),receipt_version=1)
        if len(evidence_json(details).encode())>4096:raise RepositoryError('Operation receipt is too large.')
        self._cs_insert(tx,'AUDIT_EVENT',[dict(AUDIT_ID=stable_id('cs-receipt',operation),ACTOR_USER_ID=actor['user_id'],ACTOR_EMAIL=actor['email'],ACTION='IMPORT',ENTITY_TYPE='CONTROLLED_SUPPLEMENT',ENTITY_ID=operation,DETAILS=details)])
        return details

    def _cs_verify(self,operation,kind,seal,entity,ids,tx=None):
        receipt=self._cs_receipt(operation,tx)
        if not receipt or (receipt.get('kind'),receipt.get('seal'),receipt.get('scope_sha256'),receipt.get('count'))!=(kind,seal,digest(sorted(ids)),len(ids)):raise RepositoryError('Operation receipt does not match the reviewed scope.')
        current=unique(self._cs_read(entity,ids,tx),lambda r:gid(r[TABLES[entity][1]]))
        revs=unique(self._cs_read('RECORD_REVISION',[stable_id('cs-revision',operation,entity,id) for id in ids],tx),lambda r:r['REVISION_ID'])
        audits=unique(self._cs_read('AUDIT_EVENT',[stable_id('cs-audit',operation,entity,id) for id in ids],tx),lambda r:r['AUDIT_ID'])
        if set(current)!={gid(i) for i in ids} or len(revs)!=len(ids) or len(audits)!=len(ids):raise RepositoryError('Missing/duplicate per-GUID target, revision or audit.')
        history=sorted(revs.values(),key=lambda r:r['REVISION_ID'])
        if digest([{k:r[k] for k in ['REVISION_ID','ENTITY_TYPE','ENTITY_ID','CHANGE_KIND','RECORDED_BY','REASON','BEFORE_DATA','AFTER_DATA']} for r in history])!=receipt['history_sha256']:raise RepositoryError('Committed history digest changed; do not replay.')
        for id in ids:
            rev=revs[stable_id('cs-revision',operation,entity,id)];audit=audits[stable_id('cs-audit',operation,entity,id)];after=value(rev['AFTER_DATA']);meta=after.pop('_CONTROLLED_SUPPLEMENT',None)
            if not meta or meta['operation']!=operation or meta['kind']!=kind or digest(after)!=meta['after_sha256'] or not unchanged(after,current[gid(id)]):raise RepositoryError('Committed receipt exists but current target/history differs; do not repeat the write.')
            if rev['ENTITY_TYPE']!=entity or gid(rev['ENTITY_ID'])!=gid(id) or audit['ENTITY_TYPE']!=entity or gid(audit['ENTITY_ID'])!=gid(id) or audit['ACTOR_USER_ID']!=rev['RECORDED_BY'] or value(audit['DETAILS'])['operation']!=operation or value(audit['DETAILS'])['after_sha256']!=meta['after_sha256'] or value(audit['DETAILS'])['source']!=meta['source']:raise RepositoryError('Per-GUID audit/revision scope differs.')
        return dict(status='COMMITTED_VERIFIED',operation=operation,targets=len(ids),revisions=len(revs),audits=len(audits),already_committed=True,updated=0)

    def _cs_count_fresh(self,plan,tx=None):
        from data.count_source_supplement import preview as count_preview,verify_reviewed_plan
        rows=plan['records'];ids=[r['target_guid'] for r in rows];batch={r['original_batch'] for r in rows};filehash={r['source_file_sha256'] for r in rows}
        if len(batch)!=1 or len(filehash)!=1 or len(ids)>13556:raise RepositoryError('Count supplement exceeds its single reviewed source scope.')
        batch=next(iter(batch));filehash=next(iter(filehash))
        if self._is_memory:
            wanted=set(ids)
            raw=[canonical(r) for r in self._migration_raw_rows if r['MIGRATION_BATCH_ID']==batch and r['SOURCE_ENTITY']=='FLOCK_TRANSACTION' and gid(r['SOURCE_ID']) in wanted]
            keys={(r['MIGRATION_BATCH_ID'],r['MIGRATION_RAW_ROW_ID']) for r in raw};maps=[canonical(m) for m in self._migration_id_map if (m['MIGRATION_BATCH_ID'],m['MIGRATION_RAW_ROW_ID']) in keys]
            files=copy.deepcopy(self._migration_files);bs=copy.deepcopy(self._migration_batches)
        else:
            ex=tx or self._executor();payload=evidence_json(ids)
            raw=ex.query(f"SELECT * FROM {self.database}.RAW.MIGRATION_RAW_ROW WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='FLOCK_TRANSACTION' AND UPPER(SOURCE_ID) IN (SELECT UPPER(VALUE::VARCHAR) FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))",(batch,payload)).to_dict('records')
            maps=ex.query(f"SELECT m.* FROM {self.database}.RAW.MIGRATION_ID_MAP m WHERE m.MIGRATION_BATCH_ID=%s AND m.SOURCE_ENTITY='FLOCK_TRANSACTION' AND UPPER(m.SOURCE_ID) IN (SELECT UPPER(VALUE::VARCHAR) FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))",(batch,payload)).to_dict('records')
            files=ex.query(f"SELECT * FROM {self.database}.RAW.MIGRATION_FILE WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='FLOCK_TRANSACTION'",(batch,)).to_dict('records');bs=ex.query(f'SELECT * FROM {self.database}.RAW.MIGRATION_BATCH WHERE MIGRATION_BATCH_ID=%s',(batch,)).to_dict('records')
        current=self._cs_read('FLOCK_TRANSACTION',ids,tx)
        fresh=count_preview(ids,raw,maps,current,files,bs,batch,filehash);verify_reviewed_plan(plan,fresh)
        if plan['operation_id']!=fresh['operation_id']:raise RepositoryError('Count operation identity was changed.')
        return fresh,unique(current,lambda r:gid(r['FLOCK_TRANSACTION_ID']))

    def preview_count_source_supplement(self,plan):
        self._cs_company();self._cs_count_identity(plan);fresh,_=self._cs_count_fresh(plan)
        return fresh

    def get_count_source_supplement_status(self,plan):
        self._cs_company();self._cs_count_identity(plan);op=plan['operation_id'];ids=[r['target_guid'] for r in plan['records']]
        if self._cs_receipt(op):return self._cs_verify(op,'COUNT_LABEL',plan['review_set_sha256'],'FLOCK_TRANSACTION',ids)
        return dict(status='NO_COMMITTED_RECEIPT_VISIBLE',operation=op,transaction_final_state='NOT_ESTABLISHED_DO_NOT_RETRY_BLINDLY')

    def commit_count_source_supplement(self,plan,*,confirmed=False,actor=None,progress_callback=None):
        from data.count_source_supplement import verify_reviewed_plan
        actor=self._review_actor(actor)
        if confirmed is not True:raise RepositoryError('Explicit reviewed confirmation is required.')
        self._cs_count_identity(plan)
        self._cs_company();op=plan['operation_id'];ids=[r['target_guid'] for r in plan['records']];seal=plan['review_set_sha256']
        if self._cs_receipt(op):return self._cs_verify(op,'COUNT_LABEL',seal,'FLOCK_TRANSACTION',ids)
        with self._continuity_transaction() as tx:
            session=self._cs_company(tx)
            if self._cs_receipt(op,tx):return self._cs_verify(op,'COUNT_LABEL',seal,'FLOCK_TRANSACTION',ids,tx)
            fresh,current=self._cs_count_fresh(plan,tx);processed=0
            for part in batches(fresh['records']):
                if self._is_memory:
                    frame=self._flock_transactions.copy();byid={gid(r['FLOCK_TRANSACTION_ID']):i for i,r in frame.iterrows()}
                    for r in part:
                        i=byid[r['target_guid']];frame.at[i,'COUNT_SOURCE_LABEL']=r['proposed_value'];frame.at[i,'UPDATED_AT']=max(pd.Timestamp.now(),pd.Timestamp(current[r['target_guid']]['UPDATED_AT'])+pd.Timedelta(1,unit='ns')).isoformat()
                    self._flock_transactions=frame
                else:
                    payload=[dict(ID=r['target_guid'],VERSION=r['expected_updated_at_ff9'],LABEL=r['proposed_value'],OLD=r['expected_old_value']) for r in part]
                    sql=f"/*cs:label-cas*/ UPDATE {self.database}.CORE.FLOCK_TRANSACTION SET COUNT_SOURCE_LABEL=s.LABEL,UPDATED_AT={advance_version_sql(NOW)} FROM (SELECT VALUE:ID::VARCHAR ID,TO_TIMESTAMP_NTZ(VALUE:VERSION::VARCHAR) VERSION,VALUE:LABEL::VARCHAR LABEL,IFF(IS_NULL_VALUE(VALUE:OLD),NULL,VALUE:OLD::VARCHAR) OLD FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s)))) s WHERE FLOCK_TRANSACTION_ID=s.ID AND UPDATED_AT=s.VERSION AND IFF(COUNT_SOURCE_LABEL IS NULL OR TRIM(COUNT_SOURCE_LABEL)='',NULL,COUNT_SOURCE_LABEL) IS NOT DISTINCT FROM s.OLD"
                    if tx.execute(sql,(evidence_json(payload),))!=len(part):raise ConcurrencyError('Count label CAS conflict; whole operation rolls back.')
                found=unique(self._cs_read('FLOCK_TRANSACTION',[r['target_guid'] for r in part],tx),lambda r:gid(r['FLOCK_TRANSACTION_ID']))
                if set(found)!={r['target_guid'] for r in part}:raise RepositoryError('Label readback is missing or duplicated.')
                histories=[]
                for r in part:
                    old=current[r['target_guid']];new=found[r['target_guid']]
                    if new['COUNT_SOURCE_LABEL']!=r['proposed_value'] or not unchanged(old,new,{'COUNT_SOURCE_LABEL','UPDATED_AT'}) or pd.Timestamp(new['UPDATED_AT'])<=pd.Timestamp(old['UPDATED_AT']):raise ConcurrencyError('Label readback changed an unapproved attribute or version.')
                    histories.append(dict(entity='FLOCK_TRANSACTION',guid=r['target_guid'],before=old,after=new,source={k:r[k] for k in ['original_batch','raw_row_id','raw_sha256','normalized_sha256','source_file_sha256','review_token','request_id']}))
                self._cs_history(tx,op,'COUNT_LABEL',histories,actor);processed+=len(part);progress(progress_callback,'IN_TRANSACTION_NOT_COMMITTED',processed,len(ids))
            self._cs_finish(tx,op,'COUNT_LABEL',seal,ids,actor,session);self._cs_verify(op,'COUNT_LABEL',seal,'FLOCK_TRANSACTION',ids,tx)
        progress(progress_callback,'COMMITTED',len(ids),len(ids))
        return dict(status='COMMITTED',operation=op,updated=len(ids),already_committed=False)

    def archive_controlled_case(self,plan,blobs,*,confirmed=False,actor=None):
        actor=self._review_actor(actor);self._cs_company();validate_case(plan)
        if confirmed is not True:raise RepositoryError('Source archival needs explicit confirmation.')
        self._cs_original_batch(plan)
        rebuilt=build_case(blobs,plan['policy'])
        if rebuilt['case_hash']!=plan['case_hash']:raise RepositoryError('Original bytes do not reproduce the reviewed case.')
        archived=[]
        for spec in plan['policy']['files']:
            content=bytes(blobs[spec['name']]);fileid=stable_id(ROUTE,spec['name'],spec['sha256']);path=f"@{getattr(self,'database','EFNS_DEV')}.RAW.EIMS_MIGRATION_FILES/archive/{fileid}/{fileid}"+__import__('pathlib').Path(spec['name']).suffix.lower()
            existing=self._cs_read('SOURCE_FILE',[fileid])
            if existing:
                if len(existing)!=1 or existing[0]['FILE_HASH']!=spec['sha256'] or existing[0]['ORIGINAL_FILENAME']!=spec['name'] or int(existing[0]['FILE_SIZE_BYTES'])!=spec['size'] or existing[0]['IMPORT_ROUTE']!=ROUTE or existing[0]['STAGE_PATH']!=path or bytehash(self.get_source_file_bytes(fileid))!=spec['sha256']:raise RepositoryError('Existing archive is ambiguous or changed.')
                archived.append(existing[0]);continue
            if self._is_memory:
                if fileid in self._original_bytes and bytehash(self._original_bytes[fileid])!=spec['sha256']:raise RepositoryError('Existing original bytes differ; never overwrite evidence.')
                self._original_bytes.setdefault(fileid,content)
            else:
                self._executor().put_stream(io.BytesIO(content),path)
                with self._executor().get_stream(path) as stream:
                    if bytehash(stream.read())!=spec['sha256']:raise RepositoryError('Archived original checksum failed; no CORE writes started.')
            record=dict(SOURCE_FILE_ID=fileid,ORIGINAL_FILENAME=spec['name'],FILE_HASH=spec['sha256'],FILE_SIZE_BYTES=len(content),STAGE_PATH=path,IMPORT_ROUTE=ROUTE,PARSE_STATUS='ARCHIVED',PARSE_ERROR=None,UPLOADED_BY=actor['user_id'])
            with self._continuity_transaction() as tx:
                current=self._cs_read('SOURCE_FILE',[fileid],tx)
                if current:
                    if len(current)!=1 or current[0]['FILE_HASH']!=spec['sha256']:raise RepositoryError('Archive registration changed concurrently.')
                else:self._cs_insert(tx,'SOURCE_FILE',[record])
            archived.append(record)
        return archived

    def _cs_restore_case(self,plan):
        validate_case(plan);self._cs_original_batch(plan);blobs={}
        for spec in plan['policy']['files']:
            fileid=stable_id(ROUTE,spec['name'],spec['sha256']);meta=self._cs_read('SOURCE_FILE',[fileid])
            expected=f"@{getattr(self,'database','EFNS_DEV')}.RAW.EIMS_MIGRATION_FILES/archive/{fileid}/{fileid}"+__import__('pathlib').Path(spec['name']).suffix.lower()
            if len(meta)!=1 or meta[0]['IMPORT_ROUTE']!=ROUTE or meta[0]['FILE_HASH']!=spec['sha256'] or meta[0]['ORIGINAL_FILENAME']!=spec['name'] or int(meta[0]['FILE_SIZE_BYTES'])!=spec['size'] or meta[0]['STAGE_PATH']!=expected:raise RepositoryError('Verified original archive is required before preparing CORE.')
            blobs[spec['name']]=self.get_source_file_bytes(fileid)
        rebuilt=build_case(blobs,plan['policy'])
        if rebuilt['case_hash']!=plan['case_hash']:raise RepositoryError('Archived source/mapping changed; no rebase allowed.')
        return rebuilt

    def stage_controlled_case(self,plan,*,confirmed=False,actor=None):
        actor=self._review_actor(actor);self._cs_company()
        if confirmed is not True:raise RepositoryError('Explicit source staging confirmation required.')
        rebuilt=self._cs_restore_case(plan);importid=stable_id('cs-stage',plan['operation_id']);rawrows=[]
        for r in rebuilt['records']:
            fileid=stable_id(ROUTE,r['source']['xlsx_file'],r['source']['xlsx_sha256'])
            rawrows.append(dict(RAW_ROW_ID=stable_id(importid,r['entity'],r['guid']),IMPORT_ID=importid,SOURCE_ROW_NUMBER=r['source']['xlsx']['row'],SOURCE_FILE_ID=fileid,TARGET_ENTITY=r['entity'],TARGET_ID=r['guid'],RAW_DATA=dict(case_hash=plan['case_hash'],original_batch=plan['policy']['original_batch'],record=r),VALIDATION_STATUS='HOLD' if r['phase']=='HOLD' else 'NEW',MATCH_STATUS='PRIMARY_GUID_EVIDENCE',VALIDATION_MESSAGES=r['issues']))
        with self._continuity_transaction() as tx:
            old=self._cs_read('IMPORT_BATCH',[importid],tx)
            if old:
                self._cs_staged(plan,tx);return dict(import_id=importid,already_prepared=True,core_writes=0)
            self._cs_insert(tx,'IMPORT_BATCH',[dict(IMPORT_ID=importid,FILENAME='Reviewed October29 sources',SOURCE=ROUTE,FILE_HASH=plan['case_hash'],FILE_SIZE_BYTES=sum(f['size'] for f in plan['policy']['files']),SOURCE_RECORD_COUNT=len(rawrows),ROW_COUNT=0,ERROR_COUNT=sum(r['phase']=='HOLD' for r in rebuilt['records']),STATUS='Prepared',NOTES=evidence_json(dict(case_hash=plan['case_hash'],original_batch=plan['policy']['original_batch'],prepared_by=actor['user_id'],prepared_email=actor['email'])))])
            self._cs_insert(tx,'IMPORT_RAW_ROW',rawrows);self._cs_staged(plan,tx)
        return dict(import_id=importid,already_prepared=False,core_writes=0)

    def _cs_staged(self,plan,tx=None):
        importid=stable_id('cs-stage',plan['operation_id']);batch=self._cs_read('IMPORT_BATCH',[importid],tx);rows=self._cs_read('IMPORT_RAW_ROW',tx=tx,import_id=importid)
        if len(batch)!=1 or batch[0]['FILE_HASH']!=plan['case_hash'] or batch[0]['SOURCE']!=ROUTE or int(batch[0]['SOURCE_RECORD_COUNT'])!=len(plan['records']) or len(rows)!=len(plan['records']):raise RepositoryError('Staged case identity/count is incomplete.')
        notes=value(batch[0]['NOTES'])
        if notes['case_hash']!=plan['case_hash'] or notes['original_batch']!=plan['policy']['original_batch']:raise RepositoryError('Staged case origin changed.')
        indexed=unique(rows,lambda r:(r['TARGET_ENTITY'],gid(r['TARGET_ID'])))
        for r in plan['records']:
            stored=indexed.get((r['entity'],r['guid']))
            if not stored or value(stored['RAW_DATA'])['case_hash']!=plan['case_hash'] or digest(value(stored['RAW_DATA'])['record'])!=digest(r) or stored['RAW_ROW_ID']!=stable_id(importid,r['entity'],r['guid']) or int(stored['SOURCE_ROW_NUMBER'])!=r['source']['xlsx']['row'] or stored['SOURCE_FILE_ID']!=stable_id(ROUTE,r['source']['xlsx_file'],r['source']['xlsx_sha256']):raise RepositoryError('Staged source rows changed or crossed batch identities.')
        return rows

    def _cs_verify_tracking(self,plan,phase,tx=None):
        rows=self._cs_staged(plan,tx);completed={'A','B'} if phase=='B' or self._cs_receipt(stable_id(plan['operation_id'],'B'),tx) else {'A'}
        for row in rows:
            r=value(row['RAW_DATA'])['record'];expected='COMMITTED' if r['phase'] in completed else 'HOLD' if r['phase']=='HOLD' else 'NEW'
            if row['VALIDATION_STATUS']!=expected:raise RepositoryError('Source tracking is not consistent with the committed phase.')
        batch=self._cs_read('IMPORT_BATCH',[stable_id('cs-stage',plan['operation_id'])],tx)[0]
        if batch['STATUS']!=('Committed' if 'B' in completed else 'Partially Committed') or int(batch['ROW_COUNT'])!=sum(r['phase'] in completed for r in plan['records']):raise RepositoryError('Batch status/count is not consistent with phase receipts.')

    def _cs_flock_targets_digest(self,ids,tx=None):
        targets=unique(self._cs_read('FLOCK',ids,tx),lambda r:gid(r['FLOCK_ID']))
        if set(targets)!={gid(id) for id in ids}:raise RepositoryError('Phase A target identity set is incomplete.')
        return digest([targets[id] for id in sorted(targets)])

    def verify_controlled_phase_a(self,plan):
        session=self._cs_company();validate_case(plan);op=stable_id(plan['operation_id'],'A');ids=[r['guid'] for r in plan['records'] if r['phase']=='A']
        result=self._cs_verify(op,'INCREMENT_A',plan['case_hash'],'FLOCK',ids)
        self._cs_verify_tracking(plan,'A')
        receipt=self._cs_receipt(op)
        if str(session['SESSION_ID'])==receipt['session_id']:raise RepositoryError('Phase A must be verified through an independent connection.')
        return dict(result,verification_session_id=str(session['SESSION_ID']),targets_sha256=self._cs_flock_targets_digest(ids))

    def _cs_phase_preview(self,plan,phase,tx=None,independent=None):
        validate_case(plan)
        if phase not in {'A','B'}:raise RepositoryError('Only phases A and B are supported.')
        rows=[r for r in plan['records'] if r['phase']==phase];entity='FLOCK' if phase=='A' else 'FLOCK_TRANSACTION';ids=[r['guid'] for r in rows]
        current=self._cs_read(entity,ids,tx)
        if current:raise RepositoryError('An original target GUID already exists without this phase receipt; do not overwrite.')
        parentids=sorted({gid(r['core']['ACCOUNT_ID' if phase=='A' else 'FLOCK_ID']) for r in rows});parents=self._cs_read('ACCOUNT' if phase=='A' else 'FLOCK',parentids,tx);parentindex=unique(parents,lambda r:gid(r['ACCOUNT_ID' if phase=='A' else 'FLOCK_ID']))
        if set(parentindex)!=set(parentids):raise RepositoryError('A parent target is missing or duplicated.')
        facilities=[]
        if phase=='A':
            facilityids=sorted({gid(r['core']['FACILITY_ID']) for r in rows});facilities=self._cs_read('FACILITY',facilityids,tx);fi=unique(facilities,lambda r:gid(r['FACILITY_ID']))
            if set(fi)!=set(facilityids) or any(gid(fi[gid(r['core']['FACILITY_ID'])]['ACCOUNT_ID'])!=gid(r['core']['ACCOUNT_ID']) for r in rows):raise RepositoryError('Flock/Facility Account ownership is not verified.')
        else:
            # Revalidate the current parent relationships at preview and inside
            # the owning submit transaction. Labels are never lookup evidence.
            if any(not gid(r.get('ACCOUNT_ID')) for r in parents):raise RepositoryError('A parent Flock has no Account relationship.')
            facilityids=sorted({gid(r['FACILITY_ID']) for r in parents if gid(r.get('FACILITY_ID'))});facilities=self._cs_read('FACILITY',facilityids,tx);fi=unique(facilities,lambda r:gid(r['FACILITY_ID']))
            if set(fi)!=set(facilityids):raise RepositoryError('A parent Flock Facility is missing or duplicated.')
            if any(gid(fi[gid(r['FACILITY_ID'])].get('ACCOUNT_ID'))!=gid(r['ACCOUNT_ID']) for r in parents if gid(r.get('FACILITY_ID'))):raise RepositoryError('Parent Flock/Facility Account ownership is not verified.')
            if independent is None:raise RepositoryError('Independent phase A verification is required before phase B preview.')
            a_ids=[r['guid'] for r in plan['records'] if r['phase']=='A'];a_op=stable_id(plan['operation_id'],'A')
            self._cs_verify(a_op,'INCREMENT_A',plan['case_hash'],'FLOCK',a_ids,tx)
            if self._cs_flock_targets_digest(a_ids,tx)!=independent['targets_sha256']:raise ConcurrencyError('Phase A targets changed since independent verification.')
        token=digest(dict(case_hash=plan['case_hash'],phase=phase,parents=sorted(parents,key=lambda r:gid(r['ACCOUNT_ID' if phase=='A' else 'FLOCK_ID'])),facilities=sorted(facilities,key=lambda r:gid(r['FACILITY_ID'])),target_ids=sorted(ids)))
        return dict(phase=phase,review_token=token,count=len(ids),entity=entity,ids=ids,parent_facility_null_ids=sorted(gid(r['FLOCK_ID']) for r in parents if phase=='B' and not gid(r.get('FACILITY_ID'))),parent_facility_policy='Historical NULL retained; every non-null Facility verified unique/existing/same Account')

    def _cs_mark_phase(self,tx,plan,phase,ids):
        importid=stable_id('cs-stage',plan['operation_id']);rawids=[stable_id(importid,'FLOCK' if phase=='A' else 'FLOCK_TRANSACTION',id) for id in ids]
        if self._is_memory:
            for row in self._raw_rows:
                if row.get('IMPORT_ID')==importid and row['RAW_ROW_ID'] in set(rawids):row['VALIDATION_STATUS']='COMMITTED'
            selected=[r for r in self._import_batches if r['IMPORT_ID']==importid]
            if len(selected)!=1:raise RepositoryError('Staged batch is ambiguous.')
            selected[0]['STATUS']='Partially Committed' if phase=='A' else 'Committed'
            selected[0]['ROW_COUNT']=sum(r['phase'] in ({'A'} if phase=='A' else {'A','B'}) for r in plan['records'])
        else:
            n=tx.execute(f"/*cs:mark-raw*/ UPDATE {self.database}.RAW.IMPORT_RAW_ROW SET VALIDATION_STATUS='COMMITTED',UPDATED_AT={NOW} WHERE IMPORT_ID=%s AND RAW_ROW_ID IN (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s)))) AND VALIDATION_STATUS='NEW'",(importid,evidence_json(rawids)))
            if n!=len(ids):raise RepositoryError('Staged phase rows changed; no partial success may commit.')
            count=sum(r['phase'] in ({'A'} if phase=='A' else {'A','B'}) for r in plan['records'])
            n=tx.execute(f'/*cs:mark-batch*/ UPDATE {self.database}.RAW.IMPORT_BATCH SET STATUS=%s,ROW_COUNT=%s,UPDATED_AT={NOW} WHERE IMPORT_ID=%s AND FILE_HASH=%s',('Partially Committed' if phase=='A' else 'Committed',count,importid,plan['case_hash']))
            if n!=1:raise RepositoryError('Staged batch changed; nothing may commit.')
        rows=self._cs_staged(plan,tx);marked={r['RAW_ROW_ID'] for r in rows if r['VALIDATION_STATUS']=='COMMITTED'}
        expected={stable_id(importid,r['entity'],r['guid']) for r in plan['records'] if r['phase'] in ({'A'} if phase=='A' else {'A','B'})}
        if marked!=expected or any(r['VALIDATION_STATUS']!='HOLD' for r in rows if value(r['RAW_DATA'])['record']['phase']=='HOLD'):raise RepositoryError('Phase tracking or HOLD rows differ from the reviewed source.')

    def _cs_independent_a(self,plan):
        factory=getattr(self,'_controlled_independent_reader',None)
        if not callable(factory):raise RepositoryError('An independent read-only connection factory is required; a pasted attestation is not accepted.')
        with factory() as other:
            if str(other._cs_company()['SESSION_ID'])==str(self._cs_company()['SESSION_ID']):raise RepositoryError('Independent verifier reused the write session.')
            return other.verify_controlled_phase_a(plan)

    def preview_controlled_incremental(self,plan,phase):
        self._cs_company();self._cs_restore_case(plan);self._cs_staged(plan)
        proof=self._cs_independent_a(plan) if phase=='B' else None
        return self._cs_phase_preview(plan,phase,independent=proof)

    def get_controlled_incremental_status(self,plan,phase):
        self._cs_company();validate_case(plan)
        if phase not in {'A','B'}:raise RepositoryError('Unknown phase.')
        op=stable_id(plan['operation_id'],phase);entity='FLOCK' if phase=='A' else 'FLOCK_TRANSACTION';ids=[r['guid'] for r in plan['records'] if r['phase']==phase]
        if self._cs_receipt(op):
            result=self._cs_verify(op,'INCREMENT_'+phase,plan['case_hash'],entity,ids);self._cs_verify_tracking(plan,phase);return result
        return dict(status='NO_COMMITTED_RECEIPT_VISIBLE',operation=op,transaction_final_state='NOT_ESTABLISHED_DO_NOT_RETRY_BLINDLY')

    def commit_controlled_incremental(self,plan,phase,review_token,*,confirmed=False,actor=None,progress_callback=None):
        actor=self._review_actor(actor);self._cs_company();validate_case(plan)
        if confirmed is not True or phase not in {'A','B'}:raise RepositoryError('Explicit phase review confirmation required.')
        op=stable_id(plan['operation_id'],phase);entity='FLOCK' if phase=='A' else 'FLOCK_TRANSACTION';rows=[r for r in plan['records'] if r['phase']==phase];ids=[r['guid'] for r in rows]
        if self._cs_receipt(op):
            result=self._cs_verify(op,'INCREMENT_'+phase,plan['case_hash'],entity,ids);self._cs_verify_tracking(plan,phase);return result
        self._cs_restore_case(plan);proof=self._cs_independent_a(plan) if phase=='B' else None
        with self._continuity_transaction() as tx:
            session=self._cs_company(tx)
            if self._cs_receipt(op,tx):
                result=self._cs_verify(op,'INCREMENT_'+phase,plan['case_hash'],entity,ids,tx);self._cs_verify_tracking(plan,phase,tx);return result
            self._cs_staged(plan,tx);fresh=self._cs_phase_preview(plan,phase,tx,proof)
            if fresh['review_token']!=review_token:raise ConcurrencyError('Reviewed parent/target versions changed; do not refresh approval to continue.')
            processed=0
            for part in batches(rows):
                self._cs_insert(tx,entity,[r['core'] for r in part]);found=unique(self._cs_read(entity,[r['guid'] for r in part],tx),lambda r:gid(r[TABLES[entity][1]]))
                if set(found)!={r['guid'] for r in part}:raise RepositoryError('Incremental readback has missing or duplicate targets.')
                history=[]
                for r in part:
                    target=found[r['guid']]
                    if not unchanged(canonical(r['core']),{k:target.get(k) for k in r['core']}):raise RepositoryError('Inserted business fields differ from the preserved source.')
                    history.append(dict(entity=entity,guid=r['guid'],before=None,after=target,source=dict(case_hash=plan['case_hash'],phase=phase,raw_row_id=stable_id(stable_id('cs-stage',plan['operation_id']),entity,r['guid']),source_sha256=digest(r['source']),optional_links='UNVERIFIED_LABELS_PRESERVED',parent_facility_state=('NOT_PROVIDED_HISTORICAL' if phase=='B' and gid(r['core']['FLOCK_ID']) in fresh['parent_facility_null_ids'] else 'NON_NULL_RELATION_VERIFIED'))))
                self._cs_history(tx,op,'INCREMENT_'+phase,history,actor);processed+=len(part);progress(progress_callback,'IN_TRANSACTION_NOT_COMMITTED',processed,len(ids))
            self._cs_mark_phase(tx,plan,phase,ids)
            self._cs_finish(tx,op,'INCREMENT_'+phase,plan['case_hash'],ids,actor,session);self._cs_verify(op,'INCREMENT_'+phase,plan['case_hash'],entity,ids,tx)
        progress(progress_callback,'COMMITTED',len(ids),len(ids))
        return dict(status='COMMITTED',operation=op,created=len(ids),updated=0,already_committed=False)
