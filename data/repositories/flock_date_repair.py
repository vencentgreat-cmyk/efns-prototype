"""Restricted RAW-backed date interpretation repair; never a lifecycle event."""
import copy
import datetime as dt
import hashlib
import json
from collections import Counter

import pandas as pd

from data.migration import load_mapping, load_mapping_for_version, _convert
from data.source_evidence import evidence_json
from data.repositories.base import RepositoryError, ConcurrencyError
from data.repositories.continuity import stable_id

FIELDS = ('EST_DISPOSAL', 'DISPOSAL_DATE')
KIND = 'MIGRATION_DATE_MAPPING_CORRECTION'
UNDO = 'MIGRATION_DATE_MAPPING_REVERSAL'
NOW = "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"
COMPANY_IDENTITY = dict(ORG='QDCTNKN', ACCOUNT_NAME='UW19058', LOCATOR='CB12755',
                        REGION='AWS_CA_CENTRAL_1', DB='EFNS_DEV')
IDENTITY_SQL = ('SELECT CURRENT_ORGANIZATION_NAME() AS ORG, '
                'CURRENT_ACCOUNT_NAME() AS ACCOUNT_NAME, CURRENT_ACCOUNT() AS LOCATOR, '
                'CURRENT_REGION() AS REGION, CURRENT_DATABASE() AS DB')


def key(value):
    return str(value or '').strip().upper()


def obj(value):
    return json.loads(value) if isinstance(value, str) else dict(value or {})


def pair(record):
    values = []
    for field in FIELDS:
        value, error = _convert(record.get(field), 'date', field)
        if error:
            raise RepositoryError(error)
        values.append(value)
    return tuple(values)


def fingerprint(value):
    return hashlib.sha256(evidence_json(value).encode()).hexdigest()


class FlockDateRepairRepository:
    def diagnose_flock_date_repair_context(self):
        """Safe identity-only evidence from the executor actually used by the page."""
        if self._is_memory:
            return dict(runtime='Mock', verified=False, note='Synthetic runtime; not company identity evidence.')
        return self._date_runtime_context()

    def _date_runtime_context(self, tx=None):
        executor = tx if tx is not None else self._executor()
        identity = executor.query(IDENTITY_SQL)
        report = dict(repository_database=self.database,
                      runtime=getattr(executor, 'runtime_name', type(executor).__name__),
                      result_columns=list(identity.columns), row_count=len(identity),
                      expected=COMPANY_IDENTITY.copy(), values={}, types={}, mismatches=[])
        if self.database != 'EFNS_DEV':
            report['mismatches'].append('repository_database')
        if len(identity) != 1 or len(identity.columns) != len(COMPANY_IDENTITY) or set(identity.columns) != set(COMPANY_IDENTITY):
            report['mismatches'].append('identity_result_shape_or_aliases')
        else:
            for field, expected in COMPANY_IDENTITY.items():
                value = identity[field].iloc[0]
                report['types'][field] = type(value).__name__
                report['values'][field] = value if isinstance(value, str) else None
                if not isinstance(value, str) or value != expected:
                    report['mismatches'].append(field)
        report['verified'] = not report['mismatches']
        return report

    def _date_company(self, tx=None):
        if not self._is_memory:
            if self.database!='EFNS_DEV':
                raise RepositoryError('Date repair is restricted to the verified company DEV. Mismatch: repository_database.')
            report = self._date_runtime_context(tx)
            if not report['verified']:
                error = RepositoryError('Date repair is restricted to the verified company DEV. Mismatch: '+', '.join(report['mismatches'])+'.')
                error.date_identity_diagnostic = report
                raise error

    def _date_scope(self, batch_id, tx=None):
        self._date_company(tx)
        if self._is_memory:
            batches = [copy.deepcopy(r) for r in self._migration_batches if r['MIGRATION_BATCH_ID'] == batch_id]
            raw = [copy.deepcopy(r) for r in self._migration_raw_rows if r['MIGRATION_BATCH_ID'] == batch_id and r['SOURCE_ENTITY'] == 'FLOCK']
            mappings = [copy.deepcopy(r) for r in self._migration_id_map if r['MIGRATION_BATCH_ID'] == batch_id and r['SOURCE_ENTITY'] == 'FLOCK']
        else:
            tx = tx or self._executor()
            batches = tx.query(f'SELECT * FROM {self.database}.RAW.MIGRATION_BATCH WHERE MIGRATION_BATCH_ID=%s',(batch_id,)).to_dict('records')
            raw = tx.query(f"SELECT * FROM {self.database}.RAW.MIGRATION_RAW_ROW WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='FLOCK'",(batch_id,)).to_dict('records')
            mappings = tx.query(f"SELECT * FROM {self.database}.RAW.MIGRATION_ID_MAP WHERE MIGRATION_BATCH_ID=%s AND SOURCE_ENTITY='FLOCK'",(batch_id,)).to_dict('records')
        if len(batches) != 1 or batches[0]['STATUS'] != 'COMMITTED':
            raise RepositoryError('Select one committed original migration batch.')
        original = load_mapping_for_version(batches[0]['SCHEMA_VERSION'])
        if original['schema_version'] != 'EFNS-EIMS-DATAVERSE-3':
            raise RepositoryError('This repair only interprets the preserved original v3 contract.')
        if not raw or len({r['MIGRATION_RAW_ROW_ID'] for r in raw}) != len(raw) or len({key(r['SOURCE_ID']) for r in raw}) != len(raw):
            raise RepositoryError('Source identities are missing or ambiguous inside this batch.')
        ids = [key(r['TARGET_ID']) for r in mappings]
        core, revisions, events, audits = self._date_targets(ids, tx)
        return batches[0], raw, mappings, core, revisions, events, audits

    def _date_targets(self, ids, tx=None):
        ids = sorted(set(ids))
        if self._is_memory:
            core = self._flocks[self._flocks.FLOCK_ID.astype(str).str.upper().isin(ids)].to_dict('records')
            revisions = [copy.deepcopy(r) for r in self._continuity_rows['RECORD_REVISION'] if r['ENTITY_TYPE']=='FLOCK' and key(r['ENTITY_ID']) in ids]
            events = [copy.deepcopy(r) for r in self._continuity_rows['FLOCK_EVENT'] if key(r['FLOCK_ID']) in ids]
            audits = [copy.deepcopy(r) for r in getattr(self,'_migration_review_audit',[]) if key(r.get('ENTITY_ID')) in ids]
            return core, revisions, events, audits
        if not ids:
            return [], [], [], []
        tx = tx or self._executor()
        placeholders = ','.join(['%s']*len(ids))
        queries = (
            f'SELECT * FROM {self.database}.CORE.FLOCK WHERE UPPER(FLOCK_ID) IN ({placeholders})',
            f"SELECT * FROM {self.database}.APP.RECORD_REVISION WHERE ENTITY_TYPE='FLOCK' AND UPPER(ENTITY_ID) IN ({placeholders})",
            f'SELECT * FROM {self.database}.CORE.FLOCK_EVENT WHERE UPPER(FLOCK_ID) IN ({placeholders})',
            f"SELECT * FROM {self.database}.APP.AUDIT_EVENT WHERE ACTION IN ('UPDATE','DELETE','CREATE','IMPORT') AND UPPER(ENTITY_ID) IN ({placeholders})",
        )
        return tuple(tx.query(sql,tuple(ids)).to_dict('records') for sql in queries)

    def preview_flock_date_repair(self, batch_id, basis, holds=None):
        return self._date_preview(batch_id, basis, holds)

    def _date_preview(self, batch_id, basis, holds=None, tx=None):
        if not isinstance(basis,str) or not basis.strip() or len(basis)>1500:
            raise RepositoryError('Provide a specific reviewed mapping basis (maximum 1500 characters).')
        if holds is None:
            raise RepositoryError('Supply a reviewed exclusion manifest, including an explicit empty manifest if appropriate.')
        if not isinstance(holds,dict) or any(not isinstance(v,str) or not v.strip() or len(v)>500 for v in holds.values()):
            raise RepositoryError('Exclusions must map source GUIDs to specific reasons.')
        holds = {key(k):v.strip() for k,v in holds.items()}
        batch,raw,mappings,core,revisions,events,audits = self._date_scope(batch_id,tx)
        if set(holds)-{key(r['SOURCE_ID']) for r in raw}:
            raise RepositoryError('An exclusion does not belong to this original source batch.')
        current = {}
        for row in core:
            current.setdefault(key(row['FLOCK_ID']),[]).append(row)
        revision = load_mapping()
        rows=[]
        for source in sorted(raw,key=lambda r:r['MIGRATION_RAW_ROW_ID']):
            g = key(source['SOURCE_ID'])
            matches = [r for r in mappings if r['MIGRATION_RAW_ROW_ID']==source['MIGRATION_RAW_ROW_ID']]
            candidates = current.get(g,[])
            item = dict(flock_id=g,raw_id=source['MIGRATION_RAW_ROW_ID'],source_row=source['SOURCE_ROW_NUMBER'],
                        source_file=source['SOURCE_FILENAME'],status='HOLD',reason='',before=None,proposed=None,
                        raw_hash=fingerprint(source),mapping_revision=revision['schema_version'])
            reason=None
            if source['VALIDATION_STATUS']!='READY': reason='Original source rejected; relationship decision remains separate.'
            elif (len(matches)!=1 or matches[0]['STATUS']!='COMMITTED' or key(matches[0]['SOURCE_ID'])!=g
                  or key(matches[0]['TARGET_ID'])!=g or key(source['TARGET_ID'])!=g or len(candidates)!=1):
                reason='Missing/ambiguous full source identity, committed mapping or target.'
            else:
                before = candidates[0]
                item['before']=before
                source_data = {k.upper():v for k,v in obj(source['RAW_DATA']).items()}
                normalized = obj(source['NORMALIZED_DATA'])
                try:
                    required={revision['entities']['FLOCK']['field_map'][field].upper() for field in FIELDS}
                    if not required.issubset(source_data):
                        raise RepositoryError('Original RAW date columns are missing, not confirmed NULL values.')
                    proposed = {field:_convert(source_data.get(revision['entities']['FLOCK']['field_map'][field].upper()),'date',field) for field in FIELDS}
                    if any(error for value,error in proposed.values()):
                        raise RepositoryError('Invalid original date; never infer or fill it.')
                    item['proposed']={field:value for field,(value,error) in proposed.items()}
                    if g in holds: reason=holds[g]
                    elif pair(before)==pair(item['proposed']):
                        item['status']='NO_CHANGE'
                    elif key(normalized.get('FLOCK_ID'))!=g: reason='Normalized source identity contradicts target.'
                    elif pair(before)!=pair(normalized): reason='Current dates differ from original imported values.'
                    elif pd.Timestamp(before.get('UPDATED_AT'))!=pd.Timestamp(before.get('CREATED_AT')) or pd.isna(pd.Timestamp(before.get('UPDATED_AT'))):
                        reason='Record updated since creation or version unknown; manual review required.'
                    elif any(key(r['ENTITY_ID'])==g for r in revisions): reason='Recorded attribute correction exists.'
                    elif any(key(r['FLOCK_ID'])==g for r in events): reason='Recorded business event exists.'
                    elif any(key(r.get('ENTITY_ID'))==g for r in audits): reason='Record-level write audit exists.'
                    else: item['status']='READY'
                except (RepositoryError,TypeError,ValueError) as exc:
                    reason=str(exc)
            item['reason']=reason or ''
            rows.append(item)
        payload=dict(batch_id=batch_id,batch=batch,basis=basis.strip(),holds=holds,rows=rows,
                     original_contract=load_mapping_for_version(batch['SCHEMA_VERSION']),new_contract=revision,
                     revisions=revisions,events=events,audits=audits)
        return dict(batch_id=batch_id,basis=basis.strip(),holds=holds,rows=rows,
                    counts=dict(Counter(r['status'] for r in rows)),review_token=fingerprint(payload))

    def _date_receipt(self, operation_id, tx=None):
        self._date_company(tx)
        audit_id=stable_id('flock-date-audit',operation_id)
        if self._is_memory:
            rows=[r for r in getattr(self,'_migration_review_audit',[]) if r['AUDIT_ID']==audit_id]
        else:
            rows=(tx or self._executor()).query(f'SELECT * FROM {self.database}.APP.AUDIT_EVENT WHERE AUDIT_ID=%s',(audit_id,)).to_dict('records')
        if len(rows)>1: raise RepositoryError('Ambiguous repair receipt.')
        return obj(rows[0]['DETAILS']) if rows else None

    def _date_update(self,tx,before,after):
        from data.repositories.snowflake import normalize_timestamp_bind
        if self._is_memory:
            indices=self._flocks.index[self._flocks.FLOCK_ID.astype(str).str.upper()==key(before['FLOCK_ID'])]
            if len(indices)!=1: raise ConcurrencyError('Target identity changed.')
            actual=self._flocks.loc[indices[0]].to_dict()
            if pair(actual)!=pair(before) or pd.Timestamp(actual['UPDATED_AT'])!=pd.Timestamp(before['UPDATED_AT']):
                raise ConcurrencyError('Flock dates/version changed concurrently.')
            for field in FIELDS:
                self._flocks[field]=self._flocks[field].astype(object)
                self._flocks.at[indices[0],field]=after[field]
            self._flocks.at[indices[0],'UPDATED_AT']=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            return self._flocks.loc[indices[0]].to_dict()
        affected=tx.execute(f'UPDATE {self.database}.CORE.FLOCK SET EST_DISPOSAL=%s,DISPOSAL_DATE=%s,UPDATED_AT={NOW} '
            'WHERE FLOCK_ID=%s AND UPDATED_AT=%s AND EST_DISPOSAL IS NOT DISTINCT FROM %s AND DISPOSAL_DATE IS NOT DISTINCT FROM %s',
            (*pair(after),before['FLOCK_ID'],normalize_timestamp_bind(before['UPDATED_AT']),*pair(before)))
        if affected!=1: raise ConcurrencyError('Flock dates/version changed concurrently; nothing committed.')
        found=tx.query(f'SELECT * FROM {self.database}.CORE.FLOCK WHERE FLOCK_ID=%s',(before['FLOCK_ID'],))
        if len(found)!=1: raise RepositoryError('Updated target is ambiguous.')
        return found.iloc[0].to_dict()

    def _date_revision(self,tx,record):
        if self._is_memory:
            self._continuity_rows['RECORD_REVISION'].append(copy.deepcopy(record))
            return
        fields=list(record)
        expressions=[NOW if f=='RECORDED_AT' else 'PARSE_JSON(%s)' if f in {'BEFORE_DATA','AFTER_DATA'} else '%s' for f in fields]
        params=[evidence_json(record[f]) if f in {'BEFORE_DATA','AFTER_DATA'} else record[f] for f in fields if f!='RECORDED_AT']
        affected=tx.execute(f"INSERT INTO {self.database}.APP.RECORD_REVISION ({','.join(fields)}) SELECT {','.join(expressions)}",tuple(params))
        if affected!=1: raise RepositoryError('Date correction history was not recorded exactly once.')

    def _date_finish(self,tx,operation_id,details,actor):
        record=dict(AUDIT_ID=stable_id('flock-date-audit',operation_id),
            ACTOR_USER_ID=actor['user_id'],ACTOR_EMAIL=actor['email'],ACTION='UPDATE',ENTITY_TYPE='FLOCK_DATE_REPAIR',
            ENTITY_ID=operation_id,DETAILS=details,OCCURRED_AT=dt.datetime.now(dt.timezone.utc))
        if self._is_memory:
            self._review_insert(tx,'AUDIT_EVENT',record)
        else:
            params=tuple(evidence_json(v) if k=='DETAILS' else v for k,v in record.items() if k!='OCCURRED_AT')
            affected=tx.execute(f"INSERT INTO {self.database}.APP.AUDIT_EVENT (AUDIT_ID,ACTOR_USER_ID,ACTOR_EMAIL,ACTION,ENTITY_TYPE,ENTITY_ID,DETAILS,OCCURRED_AT) SELECT %s,%s,%s,%s,%s,%s,PARSE_JSON(%s),CONVERT_TIMEZONE('UTC',CURRENT_TIMESTAMP())",params)
            if affected!=1: raise RepositoryError('Mandatory date correction audit was not recorded exactly once.')

    def commit_flock_date_repair(self,batch_id,basis,holds,review_token,*,confirmed=False,actor=None):
        actor=self._review_actor(actor)
        if confirmed is not True: raise RepositoryError('Explicit review confirmation is required.')
        self._date_company()
        operation=stable_id('flock-date-repair',batch_id,review_token)
        with self._review_transaction() as tx:
            receipt=self._date_receipt(operation,tx)
            if receipt:
                if receipt['basis']!=basis.strip() or receipt['holds']!={key(k):v.strip() for k,v in holds.items()}:
                    raise RepositoryError('Repeated repair has different review evidence.')
                self._date_verify_receipt(receipt,tx)
                return dict(operation_id=operation,changed=0,already_committed=True)
            fresh=self._date_preview(batch_id,basis,holds,tx)
            if fresh['review_token']!=review_token:
                raise ConcurrencyError('Source, contract, scope, history or current values changed; preview again.')
            ready=[r for r in fresh['rows'] if r['status']=='READY']
            if not ready: raise RepositoryError('No eligible date corrections.')
            written=[]
            for row in ready:
                after=self._date_update(tx,row['before'],row['proposed'])
                revision_id=stable_id(operation,row['raw_id'])
                self._date_revision(tx,dict(REVISION_ID=revision_id,ENTITY_TYPE='FLOCK',ENTITY_ID=row['before']['FLOCK_ID'],
                    CHANGE_KIND=KIND,BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
                    RECORDED_BY=actor['user_id'],REASON=basis.strip(),BEFORE_DATA=row['before'],
                    AFTER_DATA=dict(after,_DATE_REPAIR=dict(operation_id=operation,batch_id=batch_id,raw_id=row['raw_id'],raw_hash=row['raw_hash'],mapping_revision=row['mapping_revision'],mapping_hash=fingerprint(load_mapping())))))
                written.append(dict(flock_id=row['before']['FLOCK_ID'],revision_id=revision_id,before=row['before'],after=after))
            self._date_finish(tx,operation,dict(operation_id=operation,batch_id=batch_id,basis=basis.strip(),holds=fresh['holds'],review_token=review_token,kind=KIND,written=written),actor)
            return dict(operation_id=operation,changed=len(written),already_committed=False)

    def _date_verify_receipt(self,receipt,tx=None):
        core,revisions,events,audits=self._date_targets([key(r['flock_id']) for r in receipt['written']],tx)
        for row in receipt['written']:
            found=[c for c in core if key(c['FLOCK_ID'])==key(row['flock_id'])]
            trace=[r for r in revisions if r['REVISION_ID']==row['revision_id']]
            if (len(found)!=1 or len(trace)!=1 or pair(found[0])!=pair(row['after'])
                    or pd.Timestamp(found[0]['UPDATED_AT'])!=pd.Timestamp(row['after']['UPDATED_AT'])):
                raise ConcurrencyError('Repair target/history changed after the receipt; no replay or reversal permitted.')
            if (key(trace[0]['ENTITY_ID'])!=key(row['flock_id']) or trace[0]['CHANGE_KIND']!=receipt['kind']
                    or pair(obj(trace[0]['BEFORE_DATA']))!=pair(row['before'])
                    or pair(obj(trace[0]['AFTER_DATA']))!=pair(row['after'])):
                raise RepositoryError('Repair receipt and stored revision contradict each other.')
        return core,revisions,events,audits

    def preview_flock_date_reversal(self,operation_id,basis):
        return self._date_reversal_preview(operation_id,basis)

    def _date_reversal_preview(self,operation_id,basis,tx=None):
        if not isinstance(basis,str) or not basis.strip() or len(basis)>1500:
            raise RepositoryError('A specific reversal basis is required.')
        receipt=self._date_receipt(operation_id,tx)
        if not receipt or receipt.get('kind')!=KIND: raise RepositoryError('Original repair receipt was not found.')
        core,revisions,events,audits=self._date_verify_receipt(receipt,tx)
        own={r['revision_id'] for r in receipt['written']}
        if events or any(r['REVISION_ID'] not in own for r in revisions) or audits:
            raise RepositoryError('Other business events, changes or write audits require separate review before reversal.')
        payload=dict(operation_id=operation_id,basis=basis.strip(),receipt=receipt,core=core,revisions=revisions)
        return dict(operation_id=operation_id,basis=basis.strip(),rows=receipt['written'],review_token=fingerprint(payload))

    def commit_flock_date_reversal(self,operation_id,basis,review_token,*,confirmed=False,actor=None):
        actor=self._review_actor(actor)
        if confirmed is not True: raise RepositoryError('Explicit reversal confirmation is required.')
        self._date_company()
        reverse_id=stable_id('flock-date-reverse',operation_id,review_token)
        with self._review_transaction() as tx:
            previous=self._date_receipt(reverse_id,tx)
            if previous:
                if previous['basis']!=basis.strip(): raise RepositoryError('Reversal basis differs from the committed request.')
                self._date_verify_receipt(previous,tx)
                return dict(operation_id=reverse_id,changed=0,already_committed=True)
            fresh=self._date_reversal_preview(operation_id,basis,tx)
            if fresh['review_token']!=review_token: raise ConcurrencyError('Reversal preview changed; nothing committed.')
            written=[]
            for row in fresh['rows']:
                after=self._date_update(tx,row['after'],row['before'])
                revision_id=stable_id(reverse_id,row['revision_id'])
                self._date_revision(tx,dict(REVISION_ID=revision_id,ENTITY_TYPE='FLOCK',ENTITY_ID=row['flock_id'],
                    CHANGE_KIND=UNDO,BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),
                    RECORDED_BY=actor['user_id'],REASON=basis.strip(),BEFORE_DATA=row['after'],
                    AFTER_DATA=dict(after,_DATE_REPAIR_REVERSAL=dict(operation_id=reverse_id,original_operation=operation_id,original_revision=row['revision_id']))))
                written.append(dict(flock_id=row['flock_id'],revision_id=revision_id,before=row['after'],after=after))
            self._date_finish(tx,reverse_id,dict(operation_id=reverse_id,original_operation=operation_id,basis=basis.strip(),kind=UNDO,written=written),actor)
            return dict(operation_id=reverse_id,changed=len(written),already_committed=False)
