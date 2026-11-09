"""Shared, transaction-owned historical decision workflow for both repositories."""
from contextlib import contextmanager
import copy
import datetime as dt
from uuid import NAMESPACE_URL, uuid5

import pandas as pd

from data.correction_decisions import validated_changes, decision_json
from data.historical_corrections import build_historical_correction_preview, _variant
from data.migration import load_mapping, load_mapping_for_version, normalize_migration_row, correction_mapping
from data.migration_identity import validate_correction_sources
from data.repositories.base import RepositoryError, ConcurrencyError

NOW = "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"
RAW_TABLES = {'MIGRATION_BATCH':'_migration_batches', 'MIGRATION_RAW_ROW':'_migration_raw_rows',
              'MIGRATION_CORRECTION_BATCH':'_migration_correction_batches',
              'MIGRATION_CORRECTION_ROW':'_migration_correction_rows',
              'MIGRATION_CORRECTION_DECISION':'_migration_correction_decisions'}
CORE = {'ACCOUNT':('_accounts','ACCOUNT_ID'), 'FACILITY':('_facilities','FACILITY_ID'),
        'FLOCK':('_flocks','FLOCK_ID'), 'FLOCK_TRANSACTION':('_flock_transactions','FLOCK_TRANSACTION_ID'),
        'QUOTA_REGISTRATION':('_quota_registrations','QUOTA_ID'),
        'QUOTA_TRANSACTION':('_quota_transactions','QUOTA_TRANSACTION_ID'),
        'SALMONELLA_TEST':('_salmonella_tests','SALMONELLA_TEST_ID')}
VARIANTS = {'CHANGES','BEFORE_DATA','AFTER_DATA','CORRECTED_DATA','DETAILS'}


class CorrectionReviewRepository:
    def _review_read(self, table, batch_id, tx=None):
        key = 'MIGRATION_BATCH_ID' if table in {'MIGRATION_BATCH','MIGRATION_RAW_ROW'} else 'ORIGINAL_MIGRATION_BATCH_ID'
        if self._is_memory:
            rows = getattr(self,RAW_TABLES[table],[])
            return [copy.deepcopy(row) for row in rows if row.get(key)==batch_id
                    and (table!='MIGRATION_RAW_ROW' or row.get('VALIDATION_STATUS')=='REJECTED')]
        sql=f"SELECT * FROM {self._table(table,self.schema_raw)} WHERE {key}=%s"
        if table=='MIGRATION_RAW_ROW': sql+=" AND VALIDATION_STATUS='REJECTED'"
        return (tx or self._executor()).query(sql,(batch_id,)).to_dict('records')

    def get_historical_correction_decisions(self,batch_id):
        return pd.DataFrame(self._review_read('MIGRATION_CORRECTION_DECISION',batch_id))

    def get_historical_correction_source(self,batch_id,raw_id):
        rows=[row for row in self._review_read('MIGRATION_RAW_ROW',batch_id) if row['MIGRATION_RAW_ROW_ID']==raw_id]
        if len(rows)!=1: raise RepositoryError('The original source identity is missing or ambiguous in this batch.')
        return rows[0]

    @contextmanager
    def _review_transaction(self):
        with self._continuity_transaction() as tx:
            names=[*RAW_TABLES.values(),*[attribute for attribute,_ in CORE.values()],'_migration_review_audit']
            before={name:copy.deepcopy(getattr(self,name,[])) for name in names} if self._is_memory else {}
            try:
                yield tx
            except Exception:
                for name,value in before.items(): setattr(self,name,value)
                raise

    def _review_insert(self,tx,table,record):
        if self._is_memory:
            attribute='_migration_review_audit' if table=='AUDIT_EVENT' else RAW_TABLES[table]
            if not hasattr(self,attribute): setattr(self,attribute,[])
            getattr(self,attribute).append(copy.deepcopy(record))
            return
        target=f'{self.database}.APP.AUDIT_EVENT' if table=='AUDIT_EVENT' else self._table(table,self.schema_raw)
        columns=list(record)
        expressions=[];params=[]
        for field in columns:
            if field in {'CREATED_AT','UPDATED_AT','RECORDED_AT','COMMITTED_AT'}:
                expressions.append(NOW)
            elif field=='OCCURRED_AT':
                expressions.append("CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())")
            else:
                expressions.append('PARSE_JSON(%s)' if field in VARIANTS else '%s')
                params.append(decision_json(record[field]) if field in VARIANTS else record[field])
        tx.execute(f"INSERT INTO {target} ({', '.join(columns)}) SELECT {', '.join(expressions)}",tuple(params))

    def _review_snapshot(self,batch_id,tx=None):
        batches=self._review_read('MIGRATION_BATCH',batch_id,tx)
        if len(batches)!=1 or str(batches[0].get('STATUS')).upper()!='COMMITTED':
            raise RepositoryError('Historical corrections require one committed original migration batch.')
        frames={}
        for entity,(attribute,key) in CORE.items():
            if self._is_memory: frames[entity]=getattr(self,attribute).copy(deep=True)
            else:
                columns=[key]
                if entity in {'FACILITY','FLOCK','QUOTA_REGISTRATION'}: columns.append('ACCOUNT_ID')
                frames[entity]=(tx or self._executor()).query(f"SELECT {', '.join(columns)} FROM {self._table(entity)}")
            if key in frames[entity] and frames[entity][key].astype(str).str.casefold().duplicated().any():
                raise RepositoryError(f'{entity} has ambiguous target identities; investigate before correcting.')
        raw=self._review_read('MIGRATION_RAW_ROW',batch_id,tx)
        history=self._review_read('MIGRATION_CORRECTION_ROW',batch_id,tx)
        rounds=self._review_read('MIGRATION_CORRECTION_BATCH',batch_id,tx)
        decisions=self._review_read('MIGRATION_CORRECTION_DECISION',batch_id,tx)
        ids={entity:set(frame.get(key,pd.Series(dtype=str)).dropna().astype(str)) for entity,frame in frames.items() for key in [CORE[entity][1]]}
        owners=lambda entity,key:{str(row[key]):row.get('ACCOUNT_ID') for row in frames[entity].to_dict('records')}
        contract=self._review_contract(batches[0])
        preview=build_historical_correction_preview(batch_id,raw,ids,mapping=contract,
            quota_accounts=owners('QUOTA_REGISTRATION','QUOTA_ID'),facility_accounts=owners('FACILITY','FACILITY_ID'),
            correction_history=history,correction_batches=rounds,manual_decisions=decisions)
        return preview,raw,history,rounds,decisions,ids

    @staticmethod
    def _review_contract(batch):
        version=batch.get('SCHEMA_VERSION')
        return correction_mapping(load_mapping_for_version(version) if version else load_mapping())

    def preview_historical_correction_review(self,batch_id):
        return self._review_snapshot(batch_id)[0]

    @staticmethod
    def _review_actor(actor):
        if not isinstance(actor,dict) or not actor.get('user_id') or not str(actor.get('email','')).lower().endswith('@nsegg.ca'):
            raise RepositoryError('An authenticated internal operator is required.')
        return {'user_id':str(actor['user_id']),'email':str(actor['email']).strip().lower()}

    def _review_audit(self,tx,actor,action,entity_id,details):
        self._review_insert(tx,'AUDIT_EVENT',dict(AUDIT_ID=str(uuid5(NAMESPACE_URL,action+':'+entity_id)),
            ACTOR_USER_ID=actor['user_id'],ACTOR_EMAIL=actor['email'],ACTION=action,
            ENTITY_TYPE='MIGRATION_CORRECTION',ENTITY_ID=entity_id,DETAILS=details,
            OCCURRED_AT=dt.datetime.now(dt.timezone.utc)))

    def save_historical_correction_decision(self,batch_id,raw_id,changes,basis,expected_version,request_id,*,confirmed=False,actor=None):
        actor=self._review_actor(actor)
        basis=str(basis or '').strip()
        if confirmed is not True or not basis or len(basis)>2000:
            raise RepositoryError('A confirmation and a specific basis (maximum 2000 characters) are required.')
        if not isinstance(expected_version,int) or expected_version<0 or not isinstance(request_id,str) or not request_id or len(request_id)>128:
            raise RepositoryError('A decision version and stable request identifier are required.')
        with self._review_transaction() as tx:
            preview,raw,history,rounds,decisions,_=self._review_snapshot(batch_id,tx)
            selected=[row for row in preview.rows if row['MIGRATION_RAW_ROW_ID']==raw_id]
            if len(selected)!=1: raise RepositoryError('The original rejected row is missing or ambiguous in this batch.')
            row=selected[0]
            committed_rounds={item['MIGRATION_CORRECTION_BATCH_ID'] for item in rounds
                              if item.get('STATUS') in {'COMMITTED','COMMITTED_WITH_PENDING'}
                              and item.get('COMMITTED_AT') is not None}
            committed_source=any(item.get('MIGRATION_RAW_ROW_ID')==raw_id
                                 and item.get('DISPOSITION')=='READY_CORE'
                                 and item.get('MIGRATION_CORRECTION_BATCH_ID') in committed_rounds
                                 for item in history)
            if row['DISPOSITION']=='ALREADY_COMMITTED' or committed_source:
                raise RepositoryError('A committed correction cannot be overwritten.')
            changes=validated_changes(row['SOURCE_ENTITY'],changes)
            own=[item for item in decisions if item['MIGRATION_RAW_ROW_ID']==raw_id]
            repeats=[item for item in own if item['REQUEST_ID']==request_id]
            if repeats:
                stored=repeats[0]
                if _variant(stored['CHANGES'])!=changes or stored['BASIS']!=basis or stored['ACTOR_EMAIL']!=actor['email']:
                    raise ConcurrencyError('The save request was already used with different values.')
                return stored
            version=max([int(item['VERSION']) for item in own],default=0)
            if version!=expected_version: raise ConcurrencyError('The decision changed; reload before saving.')
            source=next(item for item in raw if item['MIGRATION_RAW_ROW_ID']==raw_id)
            mapping=self._review_contract(self._review_read('MIGRATION_BATCH',batch_id,tx)[0])
            before,_=normalize_migration_row(row['SOURCE_ENTITY'],_variant(source['RAW_DATA']),int(source['SOURCE_ROW_NUMBER']),mapping)
            decision=dict(DECISION_ID=str(uuid5(NAMESPACE_URL,decision_json([batch_id,raw_id,request_id]))),
                ORIGINAL_MIGRATION_BATCH_ID=batch_id,MIGRATION_RAW_ROW_ID=raw_id,SOURCE_ENTITY=row['SOURCE_ENTITY'],
                VERSION=version+1,REQUEST_ID=request_id,CHANGES=changes,BEFORE_DATA=before,
                AFTER_DATA={},BASIS=basis,ACTOR_EMAIL=actor['email'],STATUS='SAVED',
                RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
            # Rebuild using the same validator, not a mutable READY flag.
            latest=copy.deepcopy(source['RAW_DATA'])
            latest=_variant(latest)
            for field,value in changes.items(): latest[mapping['entities'][row['SOURCE_ENTITY']]['field_map'][field].upper()]=value
            decision['AFTER_DATA']=normalize_migration_row(row['SOURCE_ENTITY'],latest,int(source['SOURCE_ROW_NUMBER']),mapping)[0]
            if row['SOURCE_ENTITY']=='QUOTA_TRANSACTION':
                quota_id=decision['AFTER_DATA'].get('QUOTA_ID')
                if self._is_memory:
                    quotas=self._quota_registrations.to_dict('records')
                else:
                    quotas=tx.query(f"SELECT QUOTA_ID, ACCOUNT_ID FROM {self._table('QUOTA_REGISTRATION')} WHERE QUOTA_ID=%s",(quota_id,)).to_dict('records')
                owners=[item.get('ACCOUNT_ID') for item in quotas if str(item.get('QUOTA_ID')).casefold()==str(quota_id).casefold()]
                decision['AFTER_DATA']['OWNER_ACCOUNT_ID']=owners[0] if len(owners)==1 else None
            self._review_insert(tx,'MIGRATION_CORRECTION_DECISION',decision)
            self._review_audit(tx,actor,'SAVE_CORRECTION_DECISION',decision['DECISION_ID'],{'batch_id':batch_id,'raw_id':raw_id,'version':version+1,'mapping_revision':mapping['schema_version']})
            return decision

    def commit_historical_correction_review(self,batch_id,review_token,*,actor=None):
        actor=self._review_actor(actor)
        if not isinstance(review_token,str) or len(review_token)!=64:
            raise RepositoryError('Revalidate the correction preview before committing.')
        round_id=batch_id+'_REVIEW_'+review_token[:16]
        with self._review_transaction() as tx:
            preview,raw,history,rounds,decisions,ids=self._review_snapshot(batch_id,tx)
            same_round=[item for item in rounds if item['MIGRATION_CORRECTION_BATCH_ID']==round_id]
            if len(same_round)>1:
                raise RepositoryError('The correction receipt is ambiguous; investigate before retrying.')
            receipts=[item for item in same_round if item.get('COMMITTED_AT') is not None
                      and item.get('STATUS') in {'COMMITTED','COMMITTED_WITH_PENDING'}]
            if same_round and not receipts:
                raise RepositoryError('An incomplete correction receipt exists; investigate before retrying.')
            if receipts:
                written=[item for item in history if item['MIGRATION_CORRECTION_BATCH_ID']==round_id and item['DISPOSITION']=='READY_CORE']
                if not written or any(str(item['TARGET_ID']).casefold() not in {str(value).casefold() for value in ids.get(item['SOURCE_ENTITY'],set())} for item in written):
                    raise RepositoryError('The committed receipt has missing targets; investigate before retrying.')
                traced={item['MIGRATION_RAW_ROW_ID'] for item in preview.committed_rows}
                if any(item['MIGRATION_RAW_ROW_ID'] not in traced for item in written):
                    raise RepositoryError('The committed receipt has inconsistent decision/source trace; investigate before retrying.')
                return dict(correction_batch_id=round_id,counts={},idempotent=True,pending_count=len(preview.pending_rows))
            if preview.review_token!=review_token:
                raise ConcurrencyError('Decisions or validation changed after preview. Revalidate and review before committing.')
            if not preview.core_rows: raise RepositoryError('There are no validated eligible corrections.')
            validate_correction_sources(batch_id,preview.rows,raw)
            now=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            counts={}
            # Flock relationships must already exist before transaction preview;
            # this deliberately does not make its dependent rows ready in advance.
            for entity in ('QUOTA_REGISTRATION','FLOCK','FLOCK_TRANSACTION','QUOTA_TRANSACTION','SALMONELLA_TEST'):
                records=[item['CORRECTED_DATA'] for item in preview.core_rows if item['SOURCE_ENTITY']==entity]
                if not records: continue
                attribute,key=CORE[entity]
                if any(str(record[key]) in ids.get(entity,set()) for record in records):
                    raise RepositoryError('A target already exists without this committed trace; no overwrite is allowed.')
                if self._is_memory:
                    for record in records: self._upsert_frame(attribute,key,record)
                    counts[entity]=len(records)
                else:
                    count=self._insert_migration_core(tx,entity,records,require_insert_count=True)
                    if count!=len(records): raise ConcurrencyError('Target identity changed during commit; no corrections were committed.')
                    counts[entity]=count
            self._review_insert(tx,'MIGRATION_CORRECTION_BATCH',dict(MIGRATION_CORRECTION_BATCH_ID=round_id,
                ORIGINAL_MIGRATION_BATCH_ID=batch_id,STATUS='COMMITTED_WITH_PENDING' if preview.pending_rows else 'COMMITTED',
                READY_ROW_COUNT=len(preview.core_rows),PENDING_ROW_COUNT=len(preview.pending_rows),CREATED_AT=now,UPDATED_AT=now,COMMITTED_AT=now))
            for item in preview.rows:
                if item['DISPOSITION']=='ALREADY_COMMITTED': continue
                record={field:item[field] for field in ('ORIGINAL_MIGRATION_BATCH_ID','MIGRATION_RAW_ROW_ID','SOURCE_FILENAME','SOURCE_ENTITY','SOURCE_ROW_NUMBER','SOURCE_ID','TARGET_ID','DISPOSITION','RELATION_STATUS','REASON','CORRECTED_DATA','DECISION_ID','DECISION_VERSION')}
                record['REASON'] += ' Mapping revision: '+preview.mapping_revision
                record.update(MIGRATION_CORRECTION_ROW_ID=str(uuid5(NAMESPACE_URL,round_id+':'+item['MIGRATION_RAW_ROW_ID'])),MIGRATION_CORRECTION_BATCH_ID=round_id,CREATED_AT=now,UPDATED_AT=now)
                self._review_insert(tx,'MIGRATION_CORRECTION_ROW',record)
            self._review_audit(tx,actor,'COMMIT_CORRECTION_REVIEW',round_id,{'batch_id':batch_id,'counts':counts,'review_token':review_token})
            return dict(correction_batch_id=round_id,counts=counts,idempotent=False,pending_count=len(preview.pending_rows))
