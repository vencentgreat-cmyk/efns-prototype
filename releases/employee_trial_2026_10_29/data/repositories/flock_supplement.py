"""Insert-only historical Flock transaction supplements on existing evidence tables."""
from contextlib import contextmanager
import copy
import datetime as dt
import hashlib
import json
import uuid

import pandas as pd

from data.flock_transaction_supplement import (
    ROUTE, SupplementError, classify, guid, parse_associated_view,
)
from data.repositories.base import RepositoryError, ConcurrencyError
from data.repositories.continuity import stable_id
from data.source_evidence import evidence_json

NOW = "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"


class FlockSupplementRepository:
    def _supplement_snapshot(self, parsed, binding):
        flock_id = guid(binding.get("flock_id"))
        anchor_id = guid(binding.get("anchor_transaction_id"))
        batch_id = str(binding.get("original_batch_id") or "")
        if self._is_memory:
            target_rows = self._flocks[self._flocks.FLOCK_ID.astype(str).str.upper() == flock_id]
            batches = [row for row in self._migration_batches if row["MIGRATION_BATCH_ID"] == batch_id]
            lineage = [row for row in self._migration_id_map if row.get("MIGRATION_BATCH_ID") == batch_id
                       and row.get("SOURCE_ENTITY") == "FLOCK_TRANSACTION"
                       and str(row.get("TARGET_ID")).upper() == anchor_id and row.get("STATUS") == "COMMITTED"]
            raw = [row for row in self._migration_raw_rows if row.get("MIGRATION_BATCH_ID") == batch_id
                   and row.get("SOURCE_ENTITY") == "FLOCK_TRANSACTION"
                   and str(row.get("SOURCE_ID")).upper() == anchor_id]
            ids = {row['record']['FLOCK_TRANSACTION_ID'] for row in parsed.rows if row['record']}
            existing = self._flock_transactions[
                self._flock_transactions.FLOCK_TRANSACTION_ID.astype(str).str.upper().isin(ids)].to_dict('records')
        else:
            tx = self._executor()
            identity = tx.query("SELECT CURRENT_ORGANIZATION_NAME() AS ORG, CURRENT_ACCOUNT_NAME() AS ACCOUNT_NAME, CURRENT_ACCOUNT() AS LOCATOR, CURRENT_DATABASE() AS DB")
            if (len(identity) != 1 or tuple(identity.iloc[0]) != ('QDCTNKN','UW19058','CB12755','EFNS_DEV')
                    or self.database != 'EFNS_DEV'):
                raise RepositoryError("Historical supplements are restricted to the verified company DEV.")
            target_rows = tx.query(f"SELECT * FROM {self._table('FLOCK')} WHERE UPPER(FLOCK_ID)=%s",(flock_id,))
            batches = tx.query(f"SELECT * FROM {self._table('MIGRATION_BATCH',self.schema_raw)} WHERE MIGRATION_BATCH_ID=%s",(batch_id,)).to_dict('records')
            lineage = tx.query(f"SELECT * FROM {self._table('MIGRATION_ID_MAP',self.schema_raw)} WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='FLOCK_TRANSACTION' AND UPPER(TARGET_ID)=%s AND STATUS='COMMITTED'",(batch_id,anchor_id)).to_dict('records')
            raw = tx.query(f"SELECT * FROM {self._table('MIGRATION_RAW_ROW',self.schema_raw)} WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='FLOCK_TRANSACTION' AND UPPER(SOURCE_ID)=%s",(batch_id,anchor_id)).to_dict('records')
            ids = [row['record']['FLOCK_TRANSACTION_ID'] for row in parsed.rows if row['record']]
            existing = tx.query(f"SELECT * FROM {self._table('FLOCK_TRANSACTION')} WHERE UPPER(FLOCK_TRANSACTION_ID) IN ({','.join(['%s']*len(ids))})",tuple(ids)).to_dict('records') if ids else []
        if len(target_rows) != 1 or len(batches) != 1 or len(lineage) != 1 or len(raw) != 1:
            raise RepositoryError("The bound target, original batch or Delivery lineage is missing or ambiguous.")
        source = raw[0]
        normalized = source.get('NORMALIZED_DATA')
        normalized = json.loads(normalized) if isinstance(normalized,str) else normalized
        if (source.get('VALIDATION_STATUS') != 'READY'
                or lineage[0].get('MIGRATION_RAW_ROW_ID') != source.get('MIGRATION_RAW_ROW_ID')
                or not normalized or guid(normalized.get('FLOCK_ID')) != flock_id
                or guid(normalized.get('FLOCK_TRANSACTION_ID')) != anchor_id):
            raise RepositoryError("Original-batch Delivery lineage contradicts the explicit parent binding.")
        target = target_rows.iloc[0].to_dict()
        if self._is_memory:
            account_rows=self._accounts[self._accounts.ACCOUNT_ID.astype(str).str.upper()==guid(target['ACCOUNT_ID'])]
            facility_rows=self._facilities[self._facilities.FACILITY_ID.astype(str).str.upper()==guid(target['FACILITY_ID'])]
        else:
            account_rows=tx.query(f"SELECT * FROM {self._table('ACCOUNT')} WHERE UPPER(ACCOUNT_ID)=%s",(guid(target['ACCOUNT_ID']),))
            facility_rows=tx.query(f"SELECT * FROM {self._table('FACILITY')} WHERE UPPER(FACILITY_ID)=%s",(guid(target['FACILITY_ID']),))
        account=account_rows.iloc[0].to_dict() if len(account_rows)==1 else None
        facility=facility_rows.iloc[0].to_dict() if len(facility_rows)==1 else None
        return classify(parsed,binding,target,existing,batches[0],account,facility)

    def preview_flock_transaction_supplement(self, filename, content, binding):
        return self._supplement_snapshot(parse_associated_view(filename,bytes(content)),binding)

    @contextmanager
    def _supplement_transaction(self):
        # Existing lock row serializes this route across processes/connections;
        # the informational PK on target tables is NOT the concurrency guard.
        with self._continuity_transaction() as tx:
            before = copy.deepcopy((self._flock_transactions,getattr(self,'_supplement_audit',[]))) if self._is_memory else None
            try:
                yield tx
            except Exception:
                if before is not None:
                    self._flock_transactions,self._supplement_audit = before
                raise

    def _insert_supplement_transaction(self, tx, record):
        if self._is_memory:
            self._upsert_frame('_flock_transactions','FLOCK_TRANSACTION_ID',record)
            return
        columns = list(record)
        affected = tx.execute(f"INSERT INTO {self._table('FLOCK_TRANSACTION')} ({','.join(columns)},CREATED_AT,UPDATED_AT) VALUES ({','.join(['%s']*len(columns))},{NOW},{NOW})",tuple(record.values()))
        if affected != 1:
            raise RepositoryError("A supplement transaction was not inserted exactly once.")

    def _supplement_audit_event(self,tx,actor,import_id,details):
        record = dict(AUDIT_ID=str(uuid.uuid4()),ACTOR_USER_ID=actor['user_id'],
            ACTOR_EMAIL=actor['email'],ACTION='IMPORT',ENTITY_TYPE='FLOCK_TX_SUPPLEMENT',
            ENTITY_ID=import_id,DETAILS=details,OCCURRED_AT=dt.datetime.now(dt.timezone.utc))
        if self._is_memory:
            if not hasattr(self,'_supplement_audit'): self._supplement_audit=[]
            self._supplement_audit.append(record)
        else:
            # Reuse the audit encoder and server-side timestamp handling, not
            # a secondary AuthStore connection that could commit independently.
            self._review_insert(tx,'AUDIT_EVENT',record)

    def commit_flock_transaction_supplement(self,filename,content,binding,review_token,*,confirmed=False,actor=None):
        if confirmed is not True or not actor or not actor.get('user_id') or not actor.get('email'):
            raise RepositoryError("An authenticated administrator and explicit review confirmation are required.")
        content=bytes(content)
        preliminary=self.preview_flock_transaction_supplement(filename,content,binding)
        if preliminary['review_token'] != review_token:
            raise ConcurrencyError("The source, binding or reviewed target changed; preview again.")
        if not preliminary['can_commit']:
            raise RepositoryError("Resolve all CONFLICT and INVALID rows before committing this supplement.")
        # File storage cannot roll back with CORE. Successful archives remain
        # ARCHIVED and retrievable if the later database transaction fails.
        archived=self.archive_source_file(filename,content,ROUTE,actor=actor['user_id'])
        import_id=stable_id(ROUTE,binding['original_batch_id'],guid(binding['flock_id']),archived['FILE_HASH'])
        with self._supplement_transaction() as tx:
            restored=self.get_source_file_bytes(archived['SOURCE_FILE_ID'])
            if hashlib.sha256(restored).hexdigest() != preliminary['file_hash']:
                raise RepositoryError("Archived source differs from the reviewed file.")
            parsed=parse_associated_view(filename,restored)
            fresh=self._supplement_snapshot(parsed,binding)
            if fresh['review_token'] != review_token:
                raise ConcurrencyError("The reviewed target changed before the lock was acquired; preview again.")
            if not fresh['can_commit']:
                raise RepositoryError("Current targets conflict with the source; nothing was committed.")
            if self._is_memory:
                committed=[row for row in self._import_batches if row['IMPORT_ID']==import_id]
            else:
                committed=tx.query(f"SELECT * FROM {self._table('IMPORT_BATCH',self.schema_raw)} WHERE IMPORT_ID=%s",(import_id,)).to_dict('records')
            if committed:
                if (len(committed)!=1 or committed[0]['STATUS']!='Committed'
                    or json.loads(committed[0]['NOTES'])['binding']!=binding or fresh['counts']['NEW']):
                    raise RepositoryError("Existing supplement tracking is inconsistent; investigate without overwriting.")
                return dict(import_id=import_id,created_count=0,existing_count=13,updated_count=0,
                            source_rows=13,status='Committed',already_committed=True)
            for row in fresh['rows']:
                if row['classification']=='NEW':
                    self._insert_supplement_transaction(tx,row['record'])
            details=dict(binding=binding,file_hash=parsed.file_hash,source_file_id=archived['SOURCE_FILE_ID'],
                         worksheet=parsed.worksheet,counts=fresh['counts'],actor_email=actor['email'])
            batch=dict(IMPORT_ID=import_id,FILENAME=parsed.filename,SOURCE=ROUTE,
                FILE_HASH=parsed.file_hash,FILE_SIZE_BYTES=len(restored),WORKSHEET_NAME=parsed.worksheet,
                SOURCE_FILE_ID=archived['SOURCE_FILE_ID'],SOURCE_RECORD_COUNT=13,
                ROW_COUNT=fresh['counts']['NEW'],ERROR_COUNT=0,STATUS='Committed',NOTES=evidence_json(details))
            raw_rows=[dict(RAW_ROW_ID=stable_id(import_id,parsed.worksheet,row['source_row']),
                SOURCE_ROW_NUMBER=row['source_row'],SOURCE_FILE_ID=archived['SOURCE_FILE_ID'],
                TARGET_ENTITY='FLOCK_TRANSACTION',TARGET_ID=row['record']['FLOCK_TRANSACTION_ID'],
                VALIDATION_STATUS=row['classification'],MATCH_STATUS='EXPLICIT_REVIEWED_BINDING',
                VALIDATION_MESSAGES=[],RAW_DATA=dict(cells=row['raw'],logical_values=row['logical_values'],
                    metadata=parsed.metadata,binding=binding,classification=row['classification'],
                    normalized_record=row['record'],worksheet=parsed.worksheet)) for row in fresh['rows']]
            if self._is_memory:
                self.create_import_batch(batch)
                self.insert_raw_rows(import_id,raw_rows)
            else:
                self._insert_batch(tx,import_id,batch)
                if self._insert_raw(tx,import_id,raw_rows)!=13:
                    raise RepositoryError("All 13 source rows must be recorded atomically.")
            self._supplement_audit_event(tx,actor,import_id,details)
            return dict(import_id=import_id,created_count=fresh['counts']['NEW'],
                existing_count=fresh['counts']['EXISTING_MATCH'],updated_count=0,source_rows=13,status='Committed')
