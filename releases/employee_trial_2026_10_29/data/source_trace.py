"""Read-only, selected-archive historical lineage (never backfills pointers)."""
from collections import Counter, defaultdict
import datetime as dt
import json
import re

import pandas as pd

from data.repositories.base import RepositoryError

# Explicit identifier allowlist, shared by SQL and the in-memory repository.
TARGETS = {
    'ACCOUNT': ('ACCOUNT_ID', '_accounts'), 'CONTACT': ('CONTACT_ID', '_contacts'),
    'FARM_LOCATION': ('FARM_LOCATION_ID', '_farm_locations'),
    'FACILITY': ('FACILITY_ID', '_facilities'),
    'FACILITY_DETAIL': ('FACILITY_DETAIL_ID', '_facility_details'),
    'FLOCK': ('FLOCK_ID', '_flocks'),
    'FLOCK_TRANSACTION': ('FLOCK_TRANSACTION_ID', '_flock_transactions'),
    'QUOTA_REGISTRATION': ('QUOTA_ID', '_quota_registrations'),
    'QUOTA_TRANSACTION': ('QUOTA_TRANSACTION_ID', '_quota_transactions'),
    'SALMONELLA_TEST': ('SALMONELLA_TEST_ID', '_salmonella_tests'),
    'SALMONELLA_TEST_SAMPLE': ('SALMONELLA_TEST_SAMPLE_ID', '_salmonella_test_samples'),
    'PRODUCTION_RECORD': ('PRODUCTION_ID', '_production'),
    'QUOTA_ALLOCATION': ('QUOTA_ALLOCATION_ID', '_quota_allocations'),
    'DIM_EFC_DATE': ('DAY', '_efc_dates'),
}


def identity(value):
    if value is None or pd.isna(value):
        return None
    if isinstance(value, (dt.date, dt.datetime, pd.Timestamp)):
        return value.isoformat()[:10]
    return str(value).strip().upper() or None


def historical_rows(repo, file_id):
    """Resolve by archived filename + SHA-256 + byte size, then batch/RAW ID.

    EXISTS avoids multiplying RAW rows when metadata/mapping keys are only
    declared, not enforced. Ambiguous links are reported, never counted twice.
    Queries read only the selected file's rows and its referenced CORE targets.
    """
    metadata = repo._history_rows('SOURCE_FILE', 'SOURCE_FILE_ID', file_id)
    if len(metadata) > 1:
        raise RepositoryError('Archived file identity is duplicated; inspect its registration.')
    if metadata.empty or metadata.iloc[0].get('IMPORT_ROUTE') != 'HISTORICAL_EIMS':
        return pd.DataFrame()
    source = metadata.iloc[0]
    name, digest, size = source.get('ORIGINAL_FILENAME'), source.get('FILE_HASH'), source.get('FILE_SIZE_BYTES')
    if not name or not re.fullmatch(r'[0-9a-fA-F]{64}', str(digest)) or size is None or pd.isna(size):
        raise RepositoryError('Historical archive lacks a verified filename, SHA-256 or byte size.')
    params = (name, str(digest).lower(), int(size))
    if repo._is_memory:
        files = [f for f in repo._migration_files if (f.get('SOURCE_FILENAME'), str(f.get('FILE_HASH', '')).lower(), f.get('FILE_SIZE_BYTES')) == params]
    else:
        files = repo._query(f"SELECT * FROM {repo._table('MIGRATION_FILE', repo.schema_raw)} WHERE SOURCE_FILENAME=%s AND LOWER(FILE_HASH)=%s AND FILE_SIZE_BYTES=%s", params).to_dict('records')
    if not files:
        return pd.DataFrame()
    scopes = {(f['MIGRATION_BATCH_ID'], f['SOURCE_FILENAME'], f['SOURCE_ENTITY']) for f in files}
    scope_counts = Counter((f['MIGRATION_BATCH_ID'], f['SOURCE_FILENAME'], f['SOURCE_ENTITY']) for f in files)
    if repo._is_memory:
        raw = [dict(r) for r in repo._migration_raw_rows if (r['MIGRATION_BATCH_ID'], r['SOURCE_FILENAME'], r['SOURCE_ENTITY']) in scopes]
        keys = {(r['MIGRATION_BATCH_ID'], r['MIGRATION_RAW_ROW_ID']) for r in raw}
        maps = [m for m in repo._migration_id_map if (m['MIGRATION_BATCH_ID'], m['MIGRATION_RAW_ROW_ID']) in keys]
        batches = [b for b in repo._migration_batches if b['MIGRATION_BATCH_ID'] in {s[0] for s in scopes}]
    else:
        mf = repo._table('MIGRATION_FILE', repo.schema_raw)
        rr = repo._table('MIGRATION_RAW_ROW', repo.schema_raw)
        selected = f"EXISTS (SELECT 1 FROM {mf} f WHERE f.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND f.SOURCE_FILENAME=r.SOURCE_FILENAME AND f.SOURCE_ENTITY=r.SOURCE_ENTITY AND f.SOURCE_FILENAME=%s AND LOWER(f.FILE_HASH)=%s AND f.FILE_SIZE_BYTES=%s)"
        raw = repo._query(f"SELECT r.* FROM {rr} r WHERE {selected} ORDER BY r.MIGRATION_BATCH_ID,r.SOURCE_ROW_NUMBER", params).to_dict('records')
        maps = repo._query(f"SELECT m.* FROM {repo._table('MIGRATION_ID_MAP', repo.schema_raw)} m WHERE EXISTS (SELECT 1 FROM {rr} r WHERE r.MIGRATION_BATCH_ID=m.MIGRATION_BATCH_ID AND r.MIGRATION_RAW_ROW_ID=m.MIGRATION_RAW_ROW_ID AND {selected})", params).to_dict('records')
        batches = repo._query(f"SELECT b.MIGRATION_BATCH_ID,b.STATUS FROM {repo._table('MIGRATION_BATCH', repo.schema_raw)} b WHERE EXISTS (SELECT 1 FROM {mf} f WHERE f.MIGRATION_BATCH_ID=b.MIGRATION_BATCH_ID AND f.SOURCE_FILENAME=%s AND LOWER(f.FILE_HASH)=%s AND f.FILE_SIZE_BYTES=%s)", params).to_dict('records')
    raw_keys = [(r['MIGRATION_BATCH_ID'], r['MIGRATION_RAW_ROW_ID']) for r in raw]
    if any(not all(k) for k in raw_keys) or len(set(raw_keys)) != len(raw_keys):
        raise RepositoryError('Historical RAW batch/row identity is missing or duplicated; no trace can be safely displayed.')
    by_key, by_batch = defaultdict(list), defaultdict(list)
    for m in maps:
        by_key[(m['MIGRATION_BATCH_ID'], m['MIGRATION_RAW_ROW_ID'])].append(m)
    for b in batches:
        by_batch[b['MIGRATION_BATCH_ID']].append(b)
    targets = defaultdict(set)
    for m in maps:
        if identity(m.get('TARGET_ID')):
            targets[m['SOURCE_ENTITY']].add(identity(m['TARGET_ID']))
    target_counts = {}
    for entity, ids in targets.items():
        if entity not in TARGETS:
            continue
        pk, attribute = TARGETS[entity]
        if repo._is_memory:
            values = getattr(repo, attribute)[pk]
            target_counts[entity] = Counter(identity(v) for v in values if identity(v) in ids)
        else:
            expression = f"TO_CHAR({pk},'YYYY-MM-DD')" if entity == 'DIM_EFC_DATE' else f'UPPER(TO_VARCHAR({pk}))'
            result = repo._query(f"SELECT {expression} TARGET_ID,COUNT(*) TARGET_COUNT FROM {repo._table(entity, repo.schema_core)} WHERE {expression} IN (SELECT VALUE::VARCHAR FROM TABLE(FLATTEN(INPUT=>PARSE_JSON(%s)))) GROUP BY {expression}", (json.dumps(sorted(ids)),))
            target_counts[entity] = {identity(r['TARGET_ID']): int(r['TARGET_COUNT']) for r in result.to_dict('records')}
    result = []
    for r in raw:
        key = (r['MIGRATION_BATCH_ID'], r['MIGRATION_RAW_ROW_ID'])
        matches, batch = by_key[key], by_batch[key[0]]
        m = matches[0] if len(matches) == 1 else {}
        valid_link = bool(m) and all(identity(m.get(k)) == identity(r.get(k)) for k in ('SOURCE_ENTITY', 'SOURCE_ID', 'TARGET_ID'))
        status = 'Missing mapping' if not matches else 'Ambiguous mapping' if len(matches) != 1 else 'Identity mismatch' if not valid_link else m.get('STATUS')
        batch_status = batch[0].get('STATUS') if len(batch) == 1 else 'Missing or ambiguous batch'
        count = target_counts.get(r['SOURCE_ENTITY'], {}).get(identity(m.get('TARGET_ID')), 0) if valid_link else None
        confirmed = valid_link and r.get('VALIDATION_STATUS') == 'READY' and status == 'COMMITTED' and batch_status == 'COMMITTED' and count == 1 and scope_counts[(key[0], r['SOURCE_FILENAME'], r['SOURCE_ENTITY'])] == 1
        result.append(dict(r, SOURCE_TYPE='Historical migration', TRACE_BATCH_ID=key[0], TRACE_ROW_ID=key[1],
            ARCHIVE_SOURCE_FILE_ID=file_id, BATCH_STATUS=batch_status, MAPPING_STATUS=status,
            MAPPING_COUNT=len(matches), FILE_LINK_COUNT=scope_counts[(key[0], r['SOURCE_FILENAME'], r['SOURCE_ENTITY'])],
            MAPPED_TARGET_ID=m.get('TARGET_ID'), CORE_TARGET_COUNT=count,
            COMMIT_STATUS='Committed target verified' if confirmed else 'Not verified as committed',
            TRACE_METHOD='Archive filename + SHA-256 + byte size; migration batch + RAW row ID'))
    return pd.DataFrame(result)


def trace_summary(rows):
    """Source counts and distinct verified original targets, not CORE totals/new inserts."""
    if rows.empty:
        return pd.DataFrame()
    summaries = []
    for key, group in rows.groupby(['SOURCE_TYPE', 'TRACE_BATCH_ID'], dropna=False, sort=False):
        verified = group[group.COMMIT_STATUS == 'Committed target verified']
        summaries.append({'Source type': key[0], 'Batch': key[1], 'Source rows': len(group),
            'Ready rows': int(group.get('VALIDATION_STATUS', pd.Series(dtype=str)).eq('READY').sum()),
            'Rejected rows': int(group.get('VALIDATION_STATUS', pd.Series(dtype=str)).eq('REJECTED').sum()),
            'Verified committed source rows': len(verified),
            'Distinct verified targets': len({(r.get('SOURCE_ENTITY'), identity(r.get('MAPPED_TARGET_ID'))) for r in verified.to_dict('records')}),
            'Other / unverified rows': len(group) - len(verified)})
    return pd.DataFrame(summaries)


def facility_source_descriptions(repo, facility_id):
    """One selected Facility, original committed lineage only. Never a current attribute."""
    target = identity(facility_id)
    if repo._is_memory:
        if repo.get_facility(facility_id) is None:return pd.DataFrame()
    else:
        exists=repo._query(f"SELECT FACILITY_ID FROM {repo._table('FACILITY',repo.schema_core)} WHERE UPPER(FACILITY_ID)=%s",(target,))
        if len(exists)>1:raise RepositoryError('Facility identity is ambiguous.')
        if exists.empty:return pd.DataFrame()
    if repo._is_memory:
        linked=[]
        for m in repo._migration_id_map:
            if m.get('SOURCE_ENTITY')!='FACILITY' or identity(m.get('TARGET_ID'))!=target:continue
            for r in repo._migration_raw_rows:
                if (r.get('MIGRATION_BATCH_ID'),r.get('MIGRATION_RAW_ROW_ID'))!=(m.get('MIGRATION_BATCH_ID'),m.get('MIGRATION_RAW_ROW_ID')):continue
                for f in repo._migration_files:
                    if (f.get('MIGRATION_BATCH_ID'),f.get('SOURCE_FILENAME'),f.get('SOURCE_ENTITY'))!=(r.get('MIGRATION_BATCH_ID'),r.get('SOURCE_FILENAME'),r.get('SOURCE_ENTITY')):continue
                    for b in repo._migration_batches:
                        if b.get('MIGRATION_BATCH_ID')==r.get('MIGRATION_BATCH_ID'):
                            linked.append(dict(r,MAP_ENTITY=m.get('SOURCE_ENTITY'),MAP_SOURCE=m.get('SOURCE_ID'),MAP_TARGET=m.get('TARGET_ID'),MAP_STATUS=m.get('STATUS'),BATCH_STATUS=b.get('STATUS'),FILE_HASH=f.get('FILE_HASH')))
    else:
        raw=repo._table('MIGRATION_RAW_ROW',repo.schema_raw);mapping=repo._table('MIGRATION_ID_MAP',repo.schema_raw)
        files=repo._table('MIGRATION_FILE',repo.schema_raw);batch=repo._table('MIGRATION_BATCH',repo.schema_raw)
        linked=repo._query(f"SELECT r.MIGRATION_BATCH_ID,r.MIGRATION_RAW_ROW_ID,r.SOURCE_ENTITY,r.SOURCE_ID,r.TARGET_ID,r.SOURCE_FILENAME,r.SOURCE_ROW_NUMBER,r.VALIDATION_STATUS,r.RAW_DATA,m.SOURCE_ENTITY MAP_ENTITY,m.SOURCE_ID MAP_SOURCE,m.TARGET_ID MAP_TARGET,m.STATUS MAP_STATUS,b.STATUS BATCH_STATUS,f.FILE_HASH FROM {mapping} m JOIN {raw} r ON r.MIGRATION_BATCH_ID=m.MIGRATION_BATCH_ID AND r.MIGRATION_RAW_ROW_ID=m.MIGRATION_RAW_ROW_ID JOIN {files} f ON f.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID AND f.SOURCE_FILENAME=r.SOURCE_FILENAME AND f.SOURCE_ENTITY=r.SOURCE_ENTITY JOIN {batch} b ON b.MIGRATION_BATCH_ID=r.MIGRATION_BATCH_ID WHERE m.SOURCE_ENTITY='FACILITY' AND UPPER(m.TARGET_ID)=%s ORDER BY r.MIGRATION_BATCH_ID,r.SOURCE_ROW_NUMBER",(target,)).to_dict('records')
    keys=[(r['MIGRATION_BATCH_ID'],r['MIGRATION_RAW_ROW_ID']) for r in linked]
    if len(keys)!=len(set(keys)):
        raise RepositoryError('Original Facility lineage is ambiguous; do not choose one description.')
    result=[]
    for r in linked:
        if r.get('SOURCE_ENTITY')!='FACILITY' or r.get('MAP_ENTITY')!='FACILITY' or any(identity(r.get(k))!=target for k in ('SOURCE_ID','TARGET_ID','MAP_SOURCE','MAP_TARGET')):
            raise RepositoryError('Original Facility identity does not match its mapping.')
        if (r.get('VALIDATION_STATUS'),r.get('MAP_STATUS'),r.get('BATCH_STATUS'))!=('READY','COMMITTED','COMMITTED'):
            continue
        if not re.fullmatch(r'[a-fA-F0-9]{64}',str(r.get('FILE_HASH') or '')):
            raise RepositoryError('Original Facility file checksum is missing.')
        data=r.get('RAW_DATA');data=json.loads(data) if isinstance(data,str) else data
        values={str(k).lower():v for k,v in (data or {}).items()};description=values.get('efc_facilitydescription')
        if description is None or str(description).strip().casefold() in {'','null','none','nan'}:continue
        result.append({'SOURCE_TYPE':'Original migration source','DESCRIPTION':description,'MIGRATION_BATCH_ID':r['MIGRATION_BATCH_ID'],'MIGRATION_RAW_ROW_ID':r['MIGRATION_RAW_ROW_ID'],'SOURCE_FILENAME':r['SOURCE_FILENAME'],'SOURCE_ROW_NUMBER':r['SOURCE_ROW_NUMBER'],'SOURCE_FIELD':'efc_facilitydescription','FILE_SHA256':r['FILE_HASH'],'TARGET_GUID':target})
    return pd.DataFrame(result)
