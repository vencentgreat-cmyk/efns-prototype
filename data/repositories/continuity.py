"""Shared source evidence, explicit matching, and append-only business history."""
from contextlib import contextmanager
import copy
import datetime as dt
import hashlib
import io
import json
import threading
import uuid
from pathlib import Path

import pandas as pd

from data.producer_identity import resolve_producer, text
from data.repositories.base import RepositoryError, ConcurrencyError
from data.source_evidence import evidence_json

NOW = "CONVERT_TIMEZONE('UTC', CURRENT_TIMESTAMP())::TIMESTAMP_NTZ"
TABLES = {"SOURCE_FILE": "RAW", "PRODUCTION_MATCH_DECISION": "RAW",
          "FLOCK_EVENT": "CORE", "RECORD_REVISION": "APP"}
JSON_FIELDS = {"BEFORE_DATA", "AFTER_DATA"}


def stable_id(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, json.dumps(parts, default=str)))


def utc_time(value):
    value = pd.Timestamp(value)
    if pd.isna(value) or value.tzinfo is None:
        raise RepositoryError("Business time must include an explicit timezone.")
    return value.tz_convert("UTC").tz_localize(None).to_pydatetime()


def changed_attributes(before, record):
    changes = {}
    for field,value in record.items():
        if field in {"EXPECTED_UPDATED_AT", "FLOCK_ID", "FACILITY_ID"}: continue
        old = before.get(field)
        if text(old) is None and text(value) is None: continue
        if field.endswith("_DATE") or field == "EST_DISPOSAL":
            if text(old) and text(value) and pd.Timestamp(old).date() == pd.Timestamp(value).date(): continue
        try:
            if old == value: continue
        except (TypeError,ValueError): pass
        changes[field] = value
    return changes


class ContinuityRepository:
    def _init_continuity(self):
        self._continuity_lock = threading.RLock()
        self._continuity_rows = {table: [] for table in TABLES}
        self._original_bytes = {}

    @property
    def _is_memory(self):
        return hasattr(self, "_production")

    def _continuity_table(self, table):
        if table not in TABLES:
            raise RepositoryError("Unsupported continuity table.")
        return f"{self.database}.{TABLES[table]}.{table}"

    @contextmanager
    def _continuity_transaction(self):
        with self._continuity_lock:
            if not self._is_memory:
                with self._executor().transaction() as tx:
                    # Standard-table keys are informational. One provisioned
                    # control row serializes these new intake/history writers
                    # across sessions; row-CAS still detects older writers.
                    locked = tx.execute(f"UPDATE {self.database}.RAW.INTAKE_LOCK SET VERSION=VERSION+1 WHERE LOCK_ID='continuity'", ())
                    if locked != 1:
                        raise RepositoryError("The intake transaction lock is missing or not unique.")
                    yield tx
                return
            names = ("_continuity_rows", "_flocks", "_facilities", "_production", "_raw_rows", "_import_batches")
            snapshot = {name: copy.deepcopy(getattr(self, name)) for name in names}
            try:
                yield None
            except Exception:
                for name, value in snapshot.items():
                    setattr(self, name, value)
                raise

    def _history_rows(self, table, key=None, value=None, tx=None):
        if self._is_memory:
            rows = self._continuity_rows[table]
            return pd.DataFrame([copy.deepcopy(row) for row in rows if key is None or row.get(key) == value])
        sql = f"SELECT * FROM {self._continuity_table(table)}"
        if key:
            sql += f" WHERE {key} = %s"
        return (tx or self._executor()).query(sql, (value,) if key else None)

    def _append_history(self, tx, table, record):
        if self._is_memory:
            self._continuity_rows[table].append(copy.deepcopy(record))
            return
        columns = list(record)
        placeholders = ["PARSE_JSON(%s)" if field in JSON_FIELDS else "%s" for field in columns]
        params = [evidence_json(record[field]) if field in JSON_FIELDS else record[field] for field in columns]
        tx.execute(f"INSERT INTO {self._continuity_table(table)} ({', '.join(columns)}) SELECT {', '.join(placeholders)}", tuple(params))

    def archive_source_file(self, filename, content, route, actor=None):
        content = bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        file_id = stable_id(route, filename, digest)
        suffix = Path(filename).suffix.lower()
        if suffix not in {".csv", ".xlsx", ".xlsm"}:
            raise RepositoryError("Only CSV, XLSX and XLSM originals are supported.")
        path = f"@{getattr(self, 'database', 'EFNS_DEV')}.RAW.EIMS_MIGRATION_FILES/archive/{file_id}/{file_id}{suffix}"
        with self._continuity_lock:
            existing = self._history_rows("SOURCE_FILE", "SOURCE_FILE_ID", file_id)
            if not existing.empty:
                self.get_source_file_bytes(file_id)
                return existing.iloc[0].to_dict()
            if self._is_memory:
                self._original_bytes[file_id] = content
            else:
                self._executor().put_stream(io.BytesIO(content), path)
                with self._executor().get_stream(path) as stream:
                    if hashlib.sha256(stream.read()).hexdigest() != digest:
                        raise RepositoryError("Original-file archive verification failed; no business records were written.")
            record = dict(SOURCE_FILE_ID=file_id, ORIGINAL_FILENAME=filename, FILE_HASH=digest,
                          FILE_SIZE_BYTES=len(content), STAGE_PATH=path, IMPORT_ROUTE=route,
                          PARSE_STATUS="ARCHIVED", PARSE_ERROR=None, UPLOADED_BY=actor,
                          UPLOADED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
            with self._continuity_transaction() as tx:
                existing = self._history_rows("SOURCE_FILE", "SOURCE_FILE_ID", file_id, tx)
                if not existing.empty:
                    return existing.iloc[0].to_dict()
                self._append_history(tx, "SOURCE_FILE", record)
            return record

    def get_source_files(self):
        return self._history_rows("SOURCE_FILE")

    def get_source_file_bytes(self, file_id):
        frame = self._history_rows("SOURCE_FILE", "SOURCE_FILE_ID", file_id)
        if len(frame) != 1:
            raise RepositoryError("Original-file metadata is missing or ambiguous.")
        record = frame.iloc[0]
        if self._is_memory:
            content = self._original_bytes[file_id]
        else:
            with self._executor().get_stream(record.STAGE_PATH) as stream:
                content = stream.read()
        if hashlib.sha256(content).hexdigest() != record.FILE_HASH:
            raise RepositoryError("Original-file checksum does not match its archive metadata.")
        return content

    def record_source_parse(self, file_id, success, actor=None):
        # Never store exception text that could contain business data or credentials.
        status, error = ("PARSED", None) if success else ("PARSE_FAILED", "The original file could not be parsed; original bytes retained.")
        with self._continuity_transaction() as tx:
            found=self._history_rows('SOURCE_FILE','SOURCE_FILE_ID',file_id,tx)
            if len(found)!=1: raise RepositoryError('Original-file identity is missing or ambiguous.')
            before=found.iloc[0].to_dict()
            if before['PARSE_STATUS']==status and text(before.get('PARSE_ERROR'))==text(error): return
            if self._is_memory:
                for row in self._continuity_rows["SOURCE_FILE"]:
                    if row["SOURCE_FILE_ID"] == file_id:
                        row.update(PARSE_STATUS=status, PARSE_ERROR=error)
            else:
                tx.execute(f"UPDATE {self._continuity_table('SOURCE_FILE')} SET PARSE_STATUS=%s, PARSE_ERROR=%s WHERE SOURCE_FILE_ID=%s", (status, error, file_id))
            if actor:
                self._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=str(uuid.uuid4()),ENTITY_TYPE='SOURCE_FILE',ENTITY_ID=file_id,CHANGE_KIND='PARSE_REVIEW',BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor,REASON='Parser outcome; business-row validation is recorded separately',BEFORE_DATA=before,AFTER_DATA=dict(before,PARSE_STATUS=status,PARSE_ERROR=error)))

    def stage_production_upload(self, batch, raw_rows):
        file_id = batch.get("SOURCE_FILE_ID")
        if not file_id or len(self._history_rows("SOURCE_FILE", "SOURCE_FILE_ID", file_id)) != 1:
            raise RepositoryError("Archive the original workbook before staging rows.")
        import_id = stable_id("production-upload", file_id)
        if len({row['SOURCE_ROW_NUMBER'] for row in raw_rows}) != len(raw_rows):
            raise RepositoryError("Source row numbers must be unique within a workbook.")
        with self._continuity_transaction() as tx:
            existing = self.find_import_by_hash(batch["FILE_HASH"])
            if existing:
                return existing["IMPORT_ID"]
            values = dict(batch, IMPORT_ID=import_id, STATUS="Staged", ROW_COUNT=0)
            if self._is_memory:
                self.create_import_batch(values)
                self.insert_raw_rows(import_id, raw_rows)
            else:
                self._insert_batch(tx, import_id, values)
                self._insert_raw(tx, import_id, raw_rows)
        return import_id

    def stage_operational_review(self, batch, raw_rows):
        import_id = stable_id("operational-review",batch["FILE_HASH"])
        files = self.get_source_files()
        for row in raw_rows:
            if not row.get("SOURCE_FILE_ID") or len(files[files.SOURCE_FILE_ID == row["SOURCE_FILE_ID"]]) != 1:
                raise RepositoryError("Each operational source row must refer to one archived original file.")
            row["RAW_ROW_ID"] = stable_id(import_id,row["SOURCE_FILE_ID"],row["SOURCE_ROW_NUMBER"])
        if len({row['RAW_ROW_ID'] for row in raw_rows}) != len(raw_rows):
            raise RepositoryError("The same original file/row appears twice. Review each original once.")
        with self._continuity_transaction() as tx:
            existing = self.find_import_by_hash(batch["FILE_HASH"])
            if existing: return existing["IMPORT_ID"]
            values = dict(batch,IMPORT_ID=import_id,SOURCE="Daily Flock & Quota Import",STATUS="Staged",ROW_COUNT=0,SOURCE_RECORD_COUNT=len(raw_rows))
            if self._is_memory:
                self.create_import_batch(values);self.insert_raw_rows(import_id,raw_rows)
            else:
                self._insert_batch(tx,import_id,values);self._insert_raw(tx,import_id,raw_rows)
        return import_id

    def commit_staged_operational(self, import_id, records_by_entity, actor=None):
        if not any(records_by_entity.values()): raise RepositoryError("There are no accepted business rows to commit.")
        with self._continuity_transaction():
            batches = self.get_import_batches()
            found = batches[batches.IMPORT_ID == import_id]
            if len(found) != 1: raise RepositoryError("The prepared operational upload is missing or ambiguous.")
            batch = found.iloc[0].to_dict()
            if batch["STATUS"] == "Committed":
                return dict(import_id=import_id,total_count=int(batch["ROW_COUNT"]),created_count=0,updated_count=0,status="Committed",already_committed=True)
            if batch["STATUS"] != "Staged": raise RepositoryError("The upload is not ready for a commit.")
            raw = self.get_raw_rows(import_id)
            if len(raw) != int(batch["SOURCE_RECORD_COUNT"]): raise RepositoryError("The prepared source rows are incomplete.")
            prepared = []
            for row in raw.to_dict('records'):
                payload = json.loads(row['RAW_DATA']) if isinstance(row['RAW_DATA'],str) else row['RAW_DATA']
                if row['VALIDATION_STATUS']=='READY':
                    prepared.append((row['TARGET_ENTITY'],evidence_json(payload['normalized_write_record'])))
            submitted=[(entity,evidence_json(record)) for entity,records in records_by_entity.items() for record in records]
            if sorted(prepared)!=sorted(submitted): raise RepositoryError("Accepted rows differ from the prepared source review; review the original files again.")
            return self.import_operational_flock_quota_batch(dict(batch,_PREPARED_IMPORT_ID=import_id,_REVISION_ACTOR=actor),records_by_entity,raw.to_dict('records'))

    def append_operational_flock_revision(self, tx, batch, before, after):
        if not text(batch.get('_REVISION_ACTOR')):
            raise RepositoryError('Flock updates require the authenticated recorder; use the staged upload or record correction entry.')
        import_id = batch.get('IMPORT_ID') or batch.get('_PREPARED_IMPORT_ID') or batch.get('FILE_HASH')
        self._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=stable_id('operational-flock-revision',import_id,before['FLOCK_ID']),ENTITY_TYPE='FLOCK',ENTITY_ID=before['FLOCK_ID'],CHANGE_KIND='QUANTITY_CORRECTION' if any(text(before.get(k)) != text(after.get(k)) for k in ('BIRD_COUNT','BIRDS_DISPOSED')) else 'ATTRIBUTE_CORRECTION',BUSINESS_AT=None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=batch['_REVISION_ACTOR'],REASON=f'Accepted operational source update; import {import_id}. Separate business reason not supplied.',BEFORE_DATA=before,AFTER_DATA=after))

    def get_source_raw_rows(self,file_id):
        if self._is_memory: return pd.DataFrame([row for row in self._raw_rows if row.get("SOURCE_FILE_ID")==file_id])
        return self._query(f"SELECT * FROM {self._table('IMPORT_RAW_ROW',self.schema_raw)} WHERE SOURCE_FILE_ID=%s ORDER BY IMPORT_ID,SOURCE_ROW_NUMBER",(file_id,))

    def get_source_review_rows(self, file_id):
        from data.source_scope import PROVENANCE
        from data.source_trace import historical_rows
        direct = self.get_source_raw_rows(file_id).copy()
        if not direct.empty:
            direct['TRACE_METHOD'] = 'Stored SOURCE_FILE_ID'
            direct['SOURCE_TYPE'] = 'Ordinary import'
        parts = [direct]
        for import_id in PROVENANCE['legacy_file_imports'].get(file_id, []):
            legacy = self.get_raw_rows(import_id).copy()
            if not legacy.empty:
                legacy['TRACE_METHOD'] = 'Verified archive manifest; original IMPORT_ID (no backfilled file pointer)'
                legacy['SOURCE_TYPE'] = 'Legacy workbook'
                parts.append(legacy)
        for part in parts:
            if not part.empty and (part[['IMPORT_ID','RAW_ROW_ID']].isna().any().any() or part.duplicated(['IMPORT_ID','RAW_ROW_ID']).any()):
                raise RepositoryError('Retained RAW identity is missing or duplicated within a source scope; inspect the original batch.')
        result = pd.concat(parts,ignore_index=True)
        if not result.empty:
            result = result.drop_duplicates(['IMPORT_ID','RAW_ROW_ID']).sort_values(['IMPORT_ID','SOURCE_ROW_NUMBER'])
            result['TRACE_BATCH_ID'] = result['IMPORT_ID']
            result['TRACE_ROW_ID'] = result['RAW_ROW_ID']
            ids = result['IMPORT_ID'].unique().tolist()
            if self._is_memory:
                batches = [b for b in self._import_batches if b['IMPORT_ID'] in ids]
            else:
                batches = self._query(f"SELECT IMPORT_ID,STATUS FROM {self._table('IMPORT_BATCH',self.schema_raw)} WHERE IMPORT_ID IN (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s))))", (json.dumps(ids),)).to_dict('records')
            statuses = {}
            for batch in batches:
                statuses.setdefault(batch['IMPORT_ID'], []).append(batch['STATUS'])
            result['BATCH_STATUS'] = [statuses[i][0] if len(statuses.get(i, [])) == 1 else 'Missing or ambiguous batch' for i in result.IMPORT_ID]
            result['COMMIT_STATUS'] = 'Not verified by historical mapping; see ordinary import batch'
        historical = historical_rows(self, file_id)
        return pd.concat([part for part in (result, historical) if not part.empty], ignore_index=True, sort=False) if not result.empty or not historical.empty else pd.DataFrame()

    def commit_staged_production(self, import_id, actor=None, new_observations_confirmed=False):
        from data.production_intake import prepare_workbook
        with self._continuity_transaction() as tx:
            if self._is_memory:
                batches = [row for row in self._import_batches if row["IMPORT_ID"] == import_id]
                batch = batches[0] if len(batches) == 1 else None
            else:
                batches = tx.query(f"SELECT * FROM {self._table('IMPORT_BATCH', self.schema_raw)} WHERE IMPORT_ID=%s", (import_id,))
                batch = batches.iloc[0].to_dict() if len(batches) == 1 else None
            if not batch:
                raise RepositoryError("The prepared upload is missing or ambiguous.")
            if batch["STATUS"] == "Committed":
                return import_id, int(batch["ROW_COUNT"])
            if not self._is_memory:
                # Lock the batch row before any CORE insert; waiters recheck status.
                changed = tx.execute(f"UPDATE {self._table('IMPORT_BATCH', self.schema_raw)} SET UPDATED_AT={NOW} WHERE IMPORT_ID=%s AND STATUS='Staged'", (import_id,))
                if changed != 1:
                    raise ConcurrencyError("This upload was already handled; reload its status.")
            raw = self.get_raw_rows(import_id)
            expected_count = batch.get("SOURCE_RECORD_COUNT")
            if expected_count is not None and len(raw) != int(expected_count):
                raise RepositoryError("Prepared RAW rows are incomplete; no business records were committed.")
            if raw.empty or raw.SOURCE_ROW_NUMBER.duplicated().any():
                raise RepositoryError("Prepared RAW source-row identities are missing or duplicated.")
            rows = []
            for row in raw.to_dict("records"):
                payload = row["RAW_DATA"]
                payload = json.loads(payload) if isinstance(payload, str) else dict(payload)
                rows.append(dict(payload, SOURCE_ROW_NUMBER=row["SOURCE_ROW_NUMBER"]))
            records, _, _, _ = prepare_workbook(pd.DataFrame(rows), batch["SOURCE_FILE_ID"], self.get_accounts())
            if new_observations_confirmed is not True:
                raise RepositoryError("Workbook upload is not an automatic correction. A corrected workbook needs the original Production ID: use Production corrections. Otherwise explicitly confirm these are independent new observations. RAW remains Staged; no CORE write occurred.")
            count = self.insert_production_records(records, import_id) if self._is_memory else self._insert_production(tx, records, import_id)
            for record in records.to_dict("records"):
                self._append_match(tx, record, actor, "AUTO")
            if self._is_memory:
                batch.update(STATUS="Committed", ROW_COUNT=count)
            else:
                tx.execute(f"UPDATE {self._table('IMPORT_BATCH', self.schema_raw)} SET STATUS='Committed',ROW_COUNT=%s,UPDATED_AT={NOW} WHERE IMPORT_ID=%s", (count, import_id))
        return import_id, count

    def _append_match(self, tx, record, actor, handling, decision_id=None):
        decision = dict(MATCH_DECISION_ID=decision_id or str(uuid.uuid4()), PRODUCTION_ID=record["PRODUCTION_ID"],
                        SOURCE_FILE_ID=text(record.get("SOURCE_FILE_ID")), RAW_ROW_ID=text(record.get("RAW_ROW_ID")),
                        SOURCE_PRODUCER_NUMBER=text(record.get("PRODUCER_NUMBER")), ACCOUNT_ID=text(record.get("PRODUCER_ACCOUNT_ID")),
                        MATCH_STATUS=record["MATCH_STATUS"], MATCH_METHOD=record["MATCH_METHOD"],
                        MATCH_BASIS=record["MATCH_BASIS"], HANDLING=handling, RECORDED_BY=actor,
                        RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None))
        self._append_history(tx, "PRODUCTION_MATCH_DECISION", decision)

    def get_production_match_decisions(self):
        return self._history_rows("PRODUCTION_MATCH_DECISION")

    def match_production_producer(self, production_id, account_id=None, basis=None, actor=None):
        """Resolve exact source identity or record an explicit staff decision."""
        with self._continuity_transaction() as tx:
            frame = self._production[self._production.PRODUCTION_ID == production_id] if self._is_memory else tx.query(f"SELECT * FROM {self._table('PRODUCTION_RECORD')} WHERE PRODUCTION_ID=%s", (production_id,))
            if len(frame) != 1:
                raise RepositoryError("Production identity is missing or ambiguous.")
            before = frame.iloc[0].to_dict()
            if text(before.get("PRODUCER_ACCOUNT_ID")) and (not account_id or account_id != before["PRODUCER_ACCOUNT_ID"]):
                raise RepositoryError("This record already has a producer Account; do not overwrite an existing attribution.")
            accounts = self.get_accounts()
            if account_id:
                if not text(actor) or not text(basis) or len(accounts[accounts.ACCOUNT_ID == account_id]) != 1:
                    raise RepositoryError("Staff confirmation requires one existing Account, a recorder and a reason.")
                decision = dict(status="STAFF_CONFIRMED", account_id=account_id, method="STAFF_SELECTION", basis=basis)
                handling = "STAFF"
            else:
                decision = resolve_producer(before, accounts)
                handling = "AUTO"
            after = dict(before, PRODUCER_ACCOUNT_ID=decision["account_id"], MATCH_STATUS=decision["status"], MATCH_METHOD=decision["method"], MATCH_BASIS=decision["basis"])
            decision_id = stable_id("producer-match", production_id, decision["account_id"], decision["status"], decision["basis"])
            if not self._history_rows("PRODUCTION_MATCH_DECISION", "MATCH_DECISION_ID", decision_id, tx).empty:
                return decision
            now = dt.datetime.now(dt.timezone.utc).replace(tzinfo=None)
            if handling == "STAFF": after.update(MATCH_CONFIRMED_BY=actor, MATCH_CONFIRMED_AT=now)
            if self._is_memory:
                idx = frame.index[0]
                for key in ("PRODUCER_ACCOUNT_ID", "MATCH_STATUS", "MATCH_METHOD", "MATCH_BASIS", "MATCH_CONFIRMED_BY", "MATCH_CONFIRMED_AT", "UPDATED_AT"):
                    if key in self._production: self._production[key] = self._production[key].astype(object)
                    self._production.loc[idx, key] = after.get(key) if key != "UPDATED_AT" else now
            else:
                from data.repositories.snowflake import normalize_timestamp_bind
                sets = "PRODUCER_ACCOUNT_ID=%s,MATCH_STATUS=%s,MATCH_METHOD=%s,MATCH_BASIS=%s"
                params = [decision["account_id"], decision["status"], decision["method"], decision["basis"]]
                if handling == "STAFF":
                    sets += ",MATCH_CONFIRMED_BY=%s,MATCH_CONFIRMED_AT=%s"
                    params.extend([actor, now])
                params.extend([production_id, normalize_timestamp_bind(before["UPDATED_AT"]),text(before.get("PRODUCER_ACCOUNT_ID"))])
                changed = tx.execute(f"UPDATE {self._table('PRODUCTION_RECORD')} SET {sets},UPDATED_AT={NOW} WHERE PRODUCTION_ID=%s AND UPDATED_AT=%s AND PRODUCER_ACCOUNT_ID IS NOT DISTINCT FROM %s", tuple(params))
                if changed != 1: raise ConcurrencyError("Producer matching changed concurrently; reload the record.")
            self._append_match(tx, after, actor, handling, decision_id)
        return decision

    def create_manual_production(self, record, request_id, actor=None):
        from data.repositories.snowflake import PRODUCTION_DECIMAL_COLUMNS, normalize_numeric_bind
        if set(record)-({"PRODUCER_ACCOUNT_ID","REPORTING_YEAR","REPORTING_WEEK"}|PRODUCTION_DECIMAL_COLUMNS):
            raise RepositoryError("Manual intake accepts producer, reporting period and measured quantities only.")
        if not text(record.get("PRODUCER_ACCOUNT_ID")):
            raise RepositoryError("Select the producer Account before saving a new business record.")
        accounts = self.get_accounts()
        if len(accounts[accounts.ACCOUNT_ID == record["PRODUCER_ACCOUNT_ID"]]) != 1:
            raise RepositoryError("The producer Account is missing or ambiguous.")
        if not text(actor) or not text(request_id): raise RepositoryError("A recorder and request ID are required.")
        try:
            year, week = int(record["REPORTING_YEAR"]), int(record["REPORTING_WEEK"])
            if year < 1 or not 1 <= week <= 53: raise ValueError()
        except (ValueError, TypeError, KeyError):
            raise RepositoryError("A valid reporting year and week are required.") from None
        if any(text(record.get(field)) for field in ("FLOCK_ID", "FACILITY_ID", "GRADER_ACCOUNT_ID")):
            raise RepositoryError("Manual intake accepts the producer identity only; use a validated relationship workflow for other links.")
        item = dict(record, PRODUCTION_ID=stable_id("manual-production", request_id), SOURCE_TYPE="MANUAL", MATCH_STATUS="STAFF_CONFIRMED", MATCH_METHOD="STAFF_SELECTION", MATCH_BASIS="Producer Account selected for manual entry", MATCH_CONFIRMED_BY=actor,MATCH_CONFIRMED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),SOURCE_ROW_NUMBER=1,RAW_ROW_ID=stable_id("manual-raw",request_id))
        for field in PRODUCTION_DECIMAL_COLUMNS.intersection(item):
            item[field] = normalize_numeric_bind(item[field], field, 1, integer=False)
        with self._continuity_transaction() as tx:
            existing = self._production[self._production.PRODUCTION_ID == item["PRODUCTION_ID"]] if self._is_memory else tx.query(f"SELECT PRODUCTION_ID FROM {self._table('PRODUCTION_RECORD')} WHERE PRODUCTION_ID=%s", (item["PRODUCTION_ID"],))
            if not existing.empty: return item["PRODUCTION_ID"]
            import_id = stable_id("manual-production-batch", request_id)
            batch = dict(IMPORT_ID=import_id,FILENAME="Manual entry",SOURCE="Manual business entry",STATUS="Committed",ROW_COUNT=1,SOURCE_RECORD_COUNT=1)
            source = dict(RAW_ROW_ID=stable_id("manual-raw",request_id),SOURCE_ROW_NUMBER=1,RAW_DATA=dict(record),VALIDATION_STATUS="VALID",MATCH_STATUS="STAFF_CONFIRMED",VALIDATION_MESSAGES=[],TARGET_ENTITY="PRODUCTION_RECORD",TARGET_ID=item['PRODUCTION_ID'])
            if self._is_memory:
                self.create_import_batch(batch)
                self.insert_raw_rows(import_id,[source])
                self.insert_production_records(pd.DataFrame([item]), import_id)
            else:
                self._insert_batch(tx,import_id,batch)
                self._insert_raw(tx,import_id,[source])
                self._insert_production(tx, [item], import_id)
            self._append_match(tx, item, actor, "STAFF")
        return item["PRODUCTION_ID"]

    def get_flock_events(self, flock_id):
        return self._history_rows("FLOCK_EVENT", "FLOCK_ID", flock_id)

    def create_flock_with_initial_position(self, record, effective_at, reason, request_id, actor=None):
        flock_id = record.get('FLOCK_ID') or stable_id('initial-flock',request_id)
        with self._continuity_transaction():
            existing = self.get_flock(flock_id)
            if existing:
                history = self.get_flock_events(flock_id)
                initial = history[history.EVENT_ID == stable_id('flock-event',flock_id,request_id)] if not history.empty else history
                if initial.empty or any(text(existing.get(k)) != text(v) for k,v in record.items() if k != 'FLOCK_ID'):
                    raise RepositoryError('The initial-position request already belongs to a different record.')
            else:
                self.upsert_flock(dict(record,FLOCK_ID=flock_id))
            self.record_flock_event(flock_id,'INITIAL_POSITION',effective_at,reason,request_id,to_facility_id=record.get('FACILITY_ID'),actor=actor,position_confirmed=True)
        return flock_id

    def check_flock_reference_change(self, record):
        existing = self.get_flock(record.get("FLOCK_ID")) if record.get("FLOCK_ID") else None
        if existing:
            for field in ("FACILITY_ID", "DISPOSAL_DATE"):
                if field in record and text(existing.get(field)) != text(record.get(field)):
                    raise RepositoryError("Use Record Review & History to record an actual movement or end; ordinary edits cannot silently replace position/lifecycle history.")

    def check_facility_history(self, facility_id):
        events = self._history_rows("FLOCK_EVENT")
        if not events.empty and ((events.FROM_FACILITY_ID == facility_id) | (events.TO_FACILITY_ID == facility_id)).any():
            raise RepositoryError("Facility cannot be deleted while recorded business history references it.")

    def check_facility_ownership(self, record):
        current = self.get_facility(record.get('FACILITY_ID')) if record.get('FACILITY_ID') else None
        merged = dict(current or {},**record)
        if not text(merged.get('ACCOUNT_ID')) or self.get_account(merged['ACCOUNT_ID']) is None:
            raise RepositoryError('Facility requires an existing Account.')
        if current and merged['ACCOUNT_ID'] != current.get('ACCOUNT_ID'):
            linked = self.get_flocks(facility_id=record['FACILITY_ID'])
            if not linked.empty and (linked.ACCOUNT_ID != merged['ACCOUNT_ID']).any():
                raise RepositoryError('Changing Facility ownership conflicts with existing Flock Accounts; confirmation is required.')

    def get_facility(self, facility_id):
        facilities = self.get_facilities()
        found = facilities[facilities.FACILITY_ID == facility_id]
        if len(found) > 1: raise RepositoryError('Facility identity is ambiguous.')
        return found.iloc[0].to_dict() if len(found) else None

    def get_record_revisions(self):
        return self._history_rows("RECORD_REVISION")

    def get_flock_position(self, flock_id, as_of):
        events = self.get_flock_events(flock_id)
        if events.empty:
            return {"FACILITY_ID": None, "STATUS": "NO_PROVEN_HISTORY"}
        superseded = set(events.SUPERSEDES_EVENT_ID.dropna())
        active = events[~events.EVENT_ID.isin(superseded)].copy()
        active = active[active.EFFECTIVE_AT.notna() & (pd.to_datetime(active.EFFECTIVE_AT) <= utc_time(as_of))]
        if active.empty:
            return {"FACILITY_ID": None, "STATUS": "NO_PROVEN_HISTORY"}
        row = active.sort_values("EFFECTIVE_AT").iloc[-1]
        return {"FACILITY_ID": row.TO_FACILITY_ID if row.EVENT_TYPE in {"MOVE", "INITIAL_POSITION"} else None, "STATUS": row.EVENT_TYPE}

    def record_flock_event(self, flock_id, event_type, effective_at, reason, request_id,
                           to_facility_id=None, supersedes_event_id=None, actor=None, position_confirmed=False):
        if event_type not in {"MOVE", "END", "INITIAL_POSITION"} or not text(reason) or not text(request_id) or not text(actor):
            raise RepositoryError("A move or actual end requires a business time, reason, recorder and request ID.")
        if event_type in {'MOVE', 'INITIAL_POSITION'} and position_confirmed is not True:
            raise RepositoryError("Confirm the recorded origin/destination and business time from evidence; current location alone is not proof of a past movement.")
        effective = utc_time(effective_at)
        if effective > dt.datetime.now(dt.timezone.utc).replace(tzinfo=None):
            raise RepositoryError("An actual movement/end cannot be a future estimate.")
        event_id = stable_id("flock-event", flock_id, request_id)
        with self._continuity_transaction() as tx:
            history = self.get_flock_events(flock_id)
            if not history.empty and event_id in set(history.EVENT_ID):
                saved = history[history.EVENT_ID == event_id].iloc[0]
                if (saved.EVENT_TYPE != event_type or pd.Timestamp(saved.EFFECTIVE_AT) != pd.Timestamp(effective)
                    or text(saved.TO_FACILITY_ID) != text(to_facility_id) or saved.REASON != reason
                    or text(saved.SUPERSEDES_EVENT_ID) != text(supersedes_event_id)):
                    raise RepositoryError("This request ID already belongs to a different event; start another event.")
                return event_id
            flocks = self.get_flocks()
            found = flocks[flocks.FLOCK_ID == flock_id]
            if len(found) != 1:
                raise RepositoryError("Flock identity is missing or ambiguous.")
            before = found.iloc[0].to_dict()
            if event_type == 'INITIAL_POSITION':
                if not history.empty or supersedes_event_id or text(before.get('FACILITY_ID')) != text(to_facility_id) or not text(to_facility_id):
                    raise RepositoryError("An initial position requires no prior events and the explicitly confirmed recorded Facility. Never infer a historic position automatically.")
            if supersedes_event_id:
                original = history[history.EVENT_ID == supersedes_event_id] if not history.empty else history
                if len(original) != 1 or supersedes_event_id in set(history.SUPERSEDES_EVENT_ID.dropna()):
                    raise RepositoryError("The event to correct is missing or already superseded.")
            active = history[~history.EVENT_ID.isin(set(history.SUPERSEDES_EVENT_ID.dropna()))] if not history.empty else history
            if not active.empty:
                active = active[active.EVENT_ID != supersedes_event_id]
                dates = pd.to_datetime(active.EFFECTIVE_AT).dropna()
                if not dates.empty and effective <= dates.max():
                    raise RepositoryError("Use chronological business events; a correction must not invalidate later movements.")
                if "END" in set(active.EVENT_TYPE):
                    raise RepositoryError("This flock has an actual end event; correct it before recording another movement.")
            if event_type in {"MOVE", "INITIAL_POSITION"}:
                facilities = self.get_facilities()
                target = facilities[facilities.FACILITY_ID == to_facility_id]
                if len(target) != 1 or target.iloc[0].ACCOUNT_ID != before["ACCOUNT_ID"]:
                    raise RepositoryError("The destination must be one existing Facility belonging to the Flock Account; cross-Account use needs confirmation.")
            else:
                to_facility_id = None
            after = dict(before, FACILITY_ID=to_facility_id if event_type in {"MOVE", "INITIAL_POSITION"} else before.get("FACILITY_ID"))
            if event_type == "MOVE": after["FACILITY_DETAIL_ID"] = None
            if supersedes_event_id and event_type == "MOVE" and original.iloc[0].EVENT_TYPE == "END":
                previous = original.iloc[0].BEFORE_DATA
                previous = json.loads(previous) if isinstance(previous, str) else previous
                after["DISPOSAL_DATE"] = previous.get("DISPOSAL_DATE")
            if event_type == "END":
                # Store the business date in its supplied timezone, not its UTC date.
                after["DISPOSAL_DATE"] = pd.Timestamp(effective_at).date()
            if self._is_memory:
                self._upsert_frame("_flocks", "FLOCK_ID", after)
            else:
                from data.repositories.snowflake import normalize_timestamp_bind,normalize_date_bind
                updated = tx.execute(f"UPDATE {self._table('FLOCK')} SET FACILITY_ID=%s, FACILITY_DETAIL_ID=%s, DISPOSAL_DATE=%s,UPDATED_AT={NOW} WHERE FLOCK_ID=%s AND UPDATED_AT=%s", (text(after.get("FACILITY_ID")),text(after.get("FACILITY_DETAIL_ID")), normalize_date_bind(after.get("DISPOSAL_DATE")), flock_id, normalize_timestamp_bind(before["UPDATED_AT"])))
                if updated != 1:
                    raise ConcurrencyError("Flock changed during the operation; reload before retrying.")
                if not self._history_rows("FLOCK_EVENT", "EVENT_ID", event_id, tx).empty:
                    raise ConcurrencyError("This request was already handled; reload history.")
            self._append_history(tx, "FLOCK_EVENT", dict(EVENT_ID=event_id,FLOCK_ID=flock_id,EVENT_TYPE=event_type,
                FROM_FACILITY_ID=None if event_type=='INITIAL_POSITION' else text(original.iloc[0].FROM_FACILITY_ID) if supersedes_event_id and event_type=='MOVE' else text(before.get("FACILITY_ID")),TO_FACILITY_ID=to_facility_id,EFFECTIVE_AT=effective,
                RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor,REASON=reason,
                SUPERSEDES_EVENT_ID=supersedes_event_id,BEFORE_DATA=before,AFTER_DATA={**after,'POSITION_ASSERTION':'Explicitly confirmed initial Facility and business time; not inferred from a legacy snapshot' if event_type=='INITIAL_POSITION' else 'Operator confirmed the recorded origin/destination at the business time' if event_type=='MOVE' else 'Actual end asserted; last recorded Facility reference retained'}))
        return event_id

    def revise_record(self, entity, record_id, changes, reason, request_id, actor=None, business_at=None, expected_updated_at=None):
        """Attribute corrections are not quantity activities, movement, or lifecycle ends."""
        from data.repositories.snowflake import MODEL
        if entity == 'PRODUCTION_RECORD':
            return self._revise_production(record_id, changes, reason, request_id, actor, business_at, expected_updated_at)
        if entity not in {"FLOCK", "FACILITY"} or not text(reason) or not text(actor) or not text(request_id):
            raise RepositoryError("Select a Flock or Facility and supply a reason, recorder and request ID.")
        key, attributes = MODEL[entity]
        if not changes or not set(changes).issubset(set(attributes.split())):
            raise RepositoryError("Only known mutable attributes can be corrected.")
        if entity == "FLOCK" and {"FACILITY_ID", "DISPOSAL_DATE"}.intersection(changes):
            raise RepositoryError("Use explicit movement/end events for those changes, not an attribute correction.")
        revision_id = stable_id("revision", entity, record_id, request_id)
        with self._continuity_transaction() as tx:
            if not self._history_rows("RECORD_REVISION", "REVISION_ID", revision_id, tx).empty: return record_id
            before = self.get_flock(record_id) if entity == "FLOCK" else self.get_facility(record_id)
            if not before: raise RepositoryError("The record no longer exists.")
            if expected_updated_at is not None and pd.Timestamp(expected_updated_at) != pd.Timestamp(before.get("UPDATED_AT")):
                raise ConcurrencyError("This record changed after it was opened; reload it before correcting attributes.")
            kind = "QUANTITY_CORRECTION" if {"BIRD_COUNT", "BIRDS_DISPOSED"}.intersection(changes) else "ATTRIBUTE_CORRECTION"
            for field in {"BIRD_COUNT", "BIRDS_DISPOSED"}.intersection(changes):
                from data.repositories.snowflake import normalize_numeric_bind
                changes[field] = normalize_numeric_bind(changes[field],field,1,integer=True)
                if field == "BIRD_COUNT" and changes[field] is not None and changes[field] < 0:
                    raise RepositoryError("Corrected Bird Count must be a known nonnegative integer.")
            updated = dict(before, **changes, EXPECTED_UPDATED_AT=before.get("UPDATED_AT"))
            # Validate changed identity/relationships without reclassifying
            # preserved historical attributes under today's entry rules.
            if {"ACCOUNT_ID", "FACILITY_DETAIL_ID", "QUOTA_ID"}.intersection(changes):
                from data.validation import validate_flock
                if entity == "FLOCK":
                    errors = validate_flock(self,updated)
                    if errors: raise RepositoryError(" ".join(errors))
                else:
                    parents = self.get_accounts()
                    if len(parents[parents.ACCOUNT_ID == updated["ACCOUNT_ID"]]) != 1:
                        raise RepositoryError("Facility Account is missing or ambiguous.")
                    linked = self.get_flocks(facility_id=record_id)
                    if not linked.empty and (linked.ACCOUNT_ID != updated["ACCOUNT_ID"]).any():
                        raise RepositoryError("Changing Facility ownership would conflict with existing Flock Accounts; confirmation is required.")
            name = "FLOCK_NUMBER" if entity == "FLOCK" else "FACILITY_NAME"
            if name in changes and not text(changes[name]): raise RepositoryError("The business name/number cannot be empty.")
            if self._is_memory:
                self._upsert_frame("_flocks" if entity == "FLOCK" else "_facilities",key,updated)
            else:
                self._upsert_with_executor(tx,entity,{key:record_id,**changes,"EXPECTED_UPDATED_AT":before["UPDATED_AT"]})
            self._append_history(tx, "RECORD_REVISION", dict(REVISION_ID=revision_id,ENTITY_TYPE=entity,ENTITY_ID=record_id, CHANGE_KIND=kind,BUSINESS_AT=utc_time(business_at) if business_at else None, RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor,REASON=reason, BEFORE_DATA=before,AFTER_DATA={key: value for key,value in updated.items() if key != "EXPECTED_UPDATED_AT"}))
        return record_id

    def _revise_production(self, record_id, changes, reason, request_id, actor, business_at, expected_updated_at):
        from data.repositories.snowflake import PRODUCTION_DECIMAL_COLUMNS, normalize_numeric_bind, normalize_timestamp_bind
        allowed = PRODUCTION_DECIMAL_COLUMNS | {'REPORTING_YEAR', 'REPORTING_WEEK'}
        if not changes or not set(changes).issubset(allowed) or not all(text(v) for v in (reason, request_id, actor)) or expected_updated_at is None:
            raise RepositoryError("Production correction requires an original Production ID, numeric/period changes, expected version, recorder and reason. Producer attribution uses Producer matching.")
        values = {field: normalize_numeric_bind(value,field,1,integer=field in {'REPORTING_YEAR','REPORTING_WEEK'}) for field,value in changes.items()}
        for field, maximum in (('REPORTING_YEAR',9999),('REPORTING_WEEK',53)):
            if field in values and (values[field] is None or not 1 <= values[field] <= maximum):
                raise RepositoryError(f"{field} must be between 1 and {maximum}.")
        revision_id = stable_id('revision','PRODUCTION_RECORD',record_id,request_id)
        with self._continuity_transaction() as tx:
            saved = self._history_rows('RECORD_REVISION','REVISION_ID',revision_id,tx)
            if not saved.empty:
                after = saved.iloc[0].AFTER_DATA
                after = json.loads(after) if isinstance(after,str) else after
                from decimal import Decimal
                if saved.iloc[0].REASON != reason or any((text(after.get(k)) is None) != (v is None) or (v is not None and Decimal(str(after[k])) != v) for k,v in values.items()):
                    raise RepositoryError('This correction request already has different values or reason; start a new correction.')
                return record_id
            found = self._production[self._production.PRODUCTION_ID == record_id] if self._is_memory else tx.query(f"SELECT * FROM {self._table('PRODUCTION_RECORD')} WHERE PRODUCTION_ID=%s",(record_id,))
            if len(found) != 1: raise RepositoryError('The original Production ID is missing or ambiguous; no record was created.')
            before = found.iloc[0].to_dict()
            if pd.Timestamp(expected_updated_at) != pd.Timestamp(before.get('UPDATED_AT')):
                raise ConcurrencyError('Production changed after it was opened; reload before correcting it.')
            if self._is_memory:
                for field in values:
                    if field in self._production: self._production[field] = self._production[field].astype(object)
                self._upsert_frame('_production','PRODUCTION_ID',dict(PRODUCTION_ID=record_id,**values,EXPECTED_UPDATED_AT=before['UPDATED_AT']))
                after = self._production[self._production.PRODUCTION_ID == record_id].iloc[0].to_dict()
            else:
                sets = ','.join(f'{field}=%s' for field in values)
                changed = tx.execute(f"UPDATE {self._table('PRODUCTION_RECORD')} SET {sets},UPDATED_AT={NOW} WHERE PRODUCTION_ID=%s AND UPDATED_AT=%s",(*values.values(),record_id,normalize_timestamp_bind(before['UPDATED_AT'])))
                if changed != 1: raise ConcurrencyError('Production changed concurrently; no correction saved.')
                written = tx.query(f"SELECT * FROM {self._table('PRODUCTION_RECORD')} WHERE PRODUCTION_ID=%s",(record_id,))
                if len(written) != 1: raise RepositoryError('Corrected production identity is no longer unique.')
                after = written.iloc[0].to_dict()
            kind = 'QUANTITY_CORRECTION' if PRODUCTION_DECIMAL_COLUMNS.intersection(values) else 'ATTRIBUTE_CORRECTION'
            self._append_history(tx,'RECORD_REVISION',dict(REVISION_ID=revision_id,ENTITY_TYPE='PRODUCTION_RECORD',ENTITY_ID=record_id,CHANGE_KIND=kind,BUSINESS_AT=utc_time(business_at) if business_at else None,RECORDED_AT=dt.datetime.now(dt.timezone.utc).replace(tzinfo=None),RECORDED_BY=actor,REASON=reason,BEFORE_DATA=before,AFTER_DATA=after))
        return record_id
