"""Offline reconciliation and guarded SQL authoring. Never executes SQL or connects.

Only disposal business fields and the declared UPDATED_AT concurrency token can
be updated by the generated text. Input files are always opened read-only.
"""
from __future__ import annotations

import argparse
from collections import Counter
import csv
import datetime as dt
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote
from uuid import NAMESPACE_URL, UUID, uuid5

from openpyxl import load_workbook

FIELDS = ('EST_DISPOSAL', 'DISPOSAL_DATE', 'BIRDS_DISPOSED')
DATE_FIELDS = FIELDS[:2]
UNKNOWN = '<CAPTURE_FROM_BACKUP>'
KEEP = '<UNCHANGED>'
TOKEN = '<UTC_EXECUTION_TIMESTAMP>'
FORMAT = 'YYYY-MM-DD"T"HH24:MI:SS.FF9'
LEGACY_COLUMNS = ('Permit Number', 'Account', 'Estimated Disposal Date', 'Disposal Date',
                  'Birds Disposed', 'Placement Date', 'Hatch Date', 'Bird Count', 'Flock Quota Type')
EXPORT_COLUMNS = ('Flock ID', 'Flock Number', 'Account ID', 'Flock Account',
                  'Estimated Disposal Date', 'Actual Disposal Date', 'Placement Date',
                  'Hatch Date', 'Bird Count', 'Quota Type')


def text(value):
    return '' if value is None else str(value).strip()


def permit(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value == int(value):
        return str(int(value))
    return text(value)


def day(value):
    if value is None or text(value) == '':
        return None
    if isinstance(value, dt.datetime):
        return value.date().isoformat()  # Inspect stored calendar date, never timezone-shift.
    if isinstance(value, dt.date):
        return value.isoformat()
    return dt.date.fromisoformat(text(value)).isoformat()


def integer(value):
    if value is None or text(value) == '':
        return None
    try:
        number = Decimal(text(value).replace(',', ''))
    except InvalidOperation as exc:
        raise ValueError('Invalid bird quantity.') from exc
    if not number.is_finite() or number < 0 or number != number.to_integral_value():
        raise ValueError('Bird quantity must be a finite, nonnegative integer.')
    return int(number)


def account(value):
    return ' '.join(text(value).split()).casefold()


def read_inputs(legacy_path, export_path):
    workbook = load_workbook(legacy_path, read_only=True, data_only=True)
    try:
        sheet = workbook['Active Flocks'] if 'Active Flocks' in workbook.sheetnames else workbook.worksheets[0]
        source = sheet.iter_rows(values_only=True)
        headers = next(source)
        if not set(LEGACY_COLUMNS) <= set(headers):
            raise ValueError('Legacy workbook lacks required column headers.')
        legacy = [dict(zip(headers, row), SOURCE_EXCEL_ROW=index)
                  for index, row in enumerate(source, 2) if any(v is not None for v in row)]
        bindings = {}
        if 'hiddenSheet' in workbook.sheetnames:
            for row in workbook['hiddenSheet'].iter_rows(values_only=True):
                for value in row:
                    if not isinstance(value, str):
                        continue
                    for name in ('new_disposaldate', 'new_disposaldate2', 'efc_birdsdisposed'):
                        match = re.search(r'(?:^|&)' + name + r'=([^&]+)', value)
                        if match:
                            bindings[name] = unquote(match[1])
    finally:
        workbook.close()
    with Path(export_path).open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not set(EXPORT_COLUMNS) <= set(reader.fieldnames or []):
            raise ValueError('Flock export lacks required identity/date column headers.')
        current = list(reader)
    return legacy, current, bindings


def reconcile(legacy, current, *, expected_rows=14):
    """Exclude permits duplicated on either side; do not choose an arbitrary row."""
    left = Counter(permit(row['Permit Number']) for row in legacy)
    right = Counter(permit(row['Flock Number']) for row in current)
    ambiguous = {key for key in left.keys() | right.keys() if left[key] > 1 or right[key] > 1}
    by_permit = {permit(row['Flock Number']): row for row in current if right[permit(row['Flock Number'])] == 1}
    pairs = [(row, by_permit[permit(row['Permit Number'])]) for row in legacy
             if permit(row['Permit Number']) not in ambiguous and permit(row['Permit Number']) in by_permit]
    mismatches = Counter({name: 0 for name in ('EST_DISPOSAL', 'DISPOSAL_DATE', 'PLACEMENT_DATE',
                                               'HATCH_DATE', 'BIRD_COUNT', 'QUOTA_TYPE', 'ACCOUNT')})
    differences, corrections = [], []
    patterns = Counter()
    for old, new in pairs:
        before = {'EST_DISPOSAL': day(new['Estimated Disposal Date']),
                  'DISPOSAL_DATE': day(new['Actual Disposal Date'])}
        after = {'EST_DISPOSAL': day(old['Estimated Disposal Date']),
                 'DISPOSAL_DATE': day(old['Disposal Date'])}
        comparisons = {field: (after[field], before[field]) for field in DATE_FIELDS}
        comparisons.update(PLACEMENT_DATE=(day(old['Placement Date']), day(new['Placement Date'])),
                           HATCH_DATE=(day(old['Hatch Date']), day(new['Hatch Date'])),
                           BIRD_COUNT=(integer(old['Bird Count']), integer(new['Bird Count'])),
                           QUOTA_TYPE=(text(old['Flock Quota Type']), text(new['Quota Type'])),
                           ACCOUNT=(account(old['Account']), account(new['Flock Account'])))
        changes = [field for field, values in comparisons.items() if values[0] != values[1]]
        mismatches.update(changes)
        if changes:
            differences.append(dict(permit=permit(old['Permit Number']), account=text(old['Account']),
                                    changed_fields='|'.join(changes),
                                    legacy_values=json.dumps({k: comparisons[k][0] for k in changes}),
                                    current_values=json.dumps({k: comparisons[k][1] for k in changes})))
        distinct = after['EST_DISPOSAL'] != after['DISPOSAL_DATE']
        patterns['legacy_dates_distinct'] += distinct
        patterns['already_correct_distinct_pair'] += distinct and before == after
        patterns['indistinguishable_equal_legacy_dates'] += not distinct
        patterns['informative_exact_swap'] += distinct and tuple(before.values()) == tuple(reversed(tuple(after.values())))
        # Unrelated historical quantities are counted, not reclassified; the
        # current export cannot supply a comparable value for this field.
        patterns['legacy_nonblank_birds_disposed'] += text(old['Birds Disposed']) != ''
        if not any(field in changes for field in DATE_FIELDS):
            continue
        if any(field in changes for field in ('ACCOUNT', 'QUOTA_TYPE', 'BIRD_COUNT', 'HATCH_DATE')):
            raise ValueError('Correction target has unrelated identity/data discrepancies; manual review required.')
        for field in ('Flock ID', 'Account ID'):
            try:
                UUID(text(new[field]))
            except ValueError as exc:
                raise ValueError('Correction target requires valid exported Flock ID and Account ID.') from exc
        source_quantity = integer(old['Birds Disposed'])
        quantity_known = 'Birds Disposed' in new or 'BIRDS_DISPOSED' in new
        old_quantity = integer(new.get('Birds Disposed', new.get('BIRDS_DISPOSED'))) if quantity_known else UNKNOWN
        fields = [field for field in DATE_FIELDS if field in changes]
        if source_quantity is not None and (not quantity_known or source_quantity != old_quantity):
            fields.append('BIRDS_DISPOSED')
        corrections.append(dict(permit=permit(old['Permit Number']), account=text(old['Account']),
                                account_id=text(new['Account ID']), flock_id=text(new['Flock ID']),
                                source_excel_row=old['SOURCE_EXCEL_ROW'], changed_fields=fields,
                                old={**before, 'BIRDS_DISPOSED': old_quantity, 'UPDATED_AT': UNKNOWN},
                                new={**after, 'BIRDS_DISPOSED': source_quantity if 'BIRDS_DISPOSED' in fields else KEEP,
                                     'UPDATED_AT': TOKEN}))
    corrections.sort(key=lambda row: row['permit'])
    if expected_rows is not None and len(corrections) != expected_rows:
        raise ValueError(f'Expected {expected_rows} correction rows; found {len(corrections)}. Review new inputs.')
    if len({row['flock_id'].casefold() for row in corrections}) != len(corrections):
        raise ValueError('Correction targets have duplicate FLOCK_IDs.')
    summary = dict(legacy_rows=len(legacy), exported_rows=len(current), uniquely_matched=len(pairs),
                   legacy_ambiguous_rows=sum(permit(row['Permit Number']) in ambiguous for row in legacy),
                   exported_ambiguous_rows=sum(permit(row['Flock Number']) in ambiguous for row in current),
                   legacy_missing_from_export=sum(permit(row['Permit Number']) not in right for row in legacy),
                   exported_only_rows=sum(permit(row['Flock Number']) not in left for row in current),
                   field_mismatch_counts=dict(mismatches), correction_rows=len(corrections),
                   old_birds_disposed_available=all(row['old']['BIRDS_DISPOSED'] != UNKNOWN for row in corrections),
                   mapping_pattern_counts=dict(patterns))
    missing = [row for row in legacy if permit(row['Permit Number']) not in right]
    duplicates = [dict(permit=key, legacy_count=left[key], exported_count=right[key]) for key in sorted(ambiguous)]
    return corrections, summary, differences, missing, duplicates


def quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def comment(value):
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', ' '.join(str(value).splitlines()))


def literal(value, field):
    if value is None:
        return 'NULL'
    return quote(value) + '::DATE' if field in DATE_FIELDS else str(integer(value))


def business_identity(row, alias='f'):
    return f"{alias}.PERMIT_NUMBER={quote(row['permit'])} AND {alias}.ACCOUNT_ID={quote(row['account_id'])}"


def identity(row, alias='f'):
    return business_identity(row, alias) + f" AND {alias}.FLOCK_ID={quote(row['flock_id'])}"


def snapshot(alias):
    return (f"OBJECT_INSERT(OBJECT_CONSTRUCT_KEEP_NULL({alias}.*), 'UPDATED_AT', "
            f"TO_CHAR({alias}.UPDATED_AT, '{FORMAT}'), TRUE)")


def same_snapshot(alias, variable):
    values = [f"EQUAL_NULL({alias}.{field}, IFF(IS_NULL_VALUE(GET(:{variable},{quote(field)})), NULL, "
              f"GET(:{variable},{quote(field)})::{'DATE' if field in DATE_FIELDS else 'NUMBER'}))" for field in FIELDS]
    values.append(f"EQUAL_NULL(TO_CHAR({alias}.UPDATED_AT,'{FORMAT}'), GET(:{variable},'UPDATED_AT')::VARCHAR)")
    return ' AND '.join(values)


def receipts(plan_id, row, direction):
    seed = f"flock-disposal-correction:{plan_id}:{row['flock_id'].casefold()}:{direction}"
    return str(uuid5(NAMESPACE_URL, seed + ':revision')), str(uuid5(NAMESPACE_URL, seed + ':audit'))


def generate_sql(rows, plan_id, *, database='EFNS_DEV', backup='FLOCK_BACKUP_20261110',
                 actor_id='__SET_APP_USER_ID__', actor_email='__SET_APP_USER_EMAIL__', rollback=False):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', plan_id):
        raise ValueError('Unsafe plan identifier.')
    values = [actor_id, actor_email, *(row[key] for row in rows
              for key in ('permit', 'account', 'account_id', 'flock_id'))]
    if any('$$' in str(value) for value in values):
        raise ValueError('Dollar-quote delimiters require manual review.')
    for name in (database, backup):
        if not re.fullmatch(r'[A-Z][A-Z0-9_]*', name):
            raise ValueError('Unsafe SQL identifier.')
    core, saved = f'{database}.CORE.FLOCK', f'{database}.CORE.{backup}'
    revisions, audit = f'{database}.APP.RECORD_REVISION', f'{database}.APP.AUDIT_EVENT'
    direction = 'rollback' if rollback else 'apply'
    predicates = ' OR\n        '.join('(' + identity(row) + ')' for row in rows)
    body = [f"-- REVIEW ONLY: generated offline, never executed. Plan {plan_id}; {direction}.",
            '-- Run precheck.sql and review the results first. Supply the reviewed APP actor identity.',
            '-- Run standalone with staff edits paused; do not run inside another transaction.',
            'EXECUTE IMMEDIATE $$', 'DECLARE',
            "  guard_failed EXCEPTION (-20001, 'Disposal correction guard failed: identity, snapshot, history or row count.');",
            '  started BOOLEAN DEFAULT FALSE;', '  n INTEGER;', '  receipt_count INTEGER;', '  audit_count INTEGER;',
            '  before_row VARIANT;', '  after_row VARIANT;', '  receipt_after VARIANT;', '  backup_receipt VARIANT;',
            f'  actor_id VARCHAR DEFAULT {quote(actor_id)};', f'  actor_email VARCHAR DEFAULT {quote(actor_email)};',
            'BEGIN', "  IF (CURRENT_TRANSACTION() IS NOT NULL OR actor_id='__SET_APP_USER_ID__' OR actor_email='__SET_APP_USER_EMAIL__' OR TRIM(actor_id)='' OR TRIM(actor_email)='') THEN",
            '    RAISE guard_failed;', '  END IF;']
    if not rollback:
        body += ['  -- DDL occurs BEFORE the DML transaction. Never replace or recreate an existing backup.',
                 f'  CREATE TABLE IF NOT EXISTS {saved} AS SELECT f.* FROM {core} f WHERE',
                 '        ' + predicates + ';']
    body += ['  BEGIN TRANSACTION;', '  started := TRUE;', f'  SELECT COUNT(*) INTO :n FROM {saved};',
             f'  IF (n <> {len(rows)}) THEN RAISE guard_failed; END IF;']
    for row in rows:
        revision_id, audit_id = receipts(plan_id, row, direction)
        apply_revision, _ = receipts(plan_id, row, 'apply')
        kind = 'MIGRATION_DATE_MAPPING_REVERSAL' if rollback else 'MIGRATION_DATE_MAPPING_CORRECTION'
        reason = f'Legacy disposal reconciliation 2026-11-10; {direction}; plan {plan_id}'
        key, old_key = identity(row), identity(row, 'b')
        body += [f"  -- Permit {comment(row['permit'])} / {comment(row['account'])}: expected exactly one identity.",
                 f'  SELECT COUNT(*) INTO :n FROM {core} f WHERE {business_identity(row)};',
                 '  IF (n <> 1) THEN RAISE guard_failed; END IF;',
                 f'  SELECT COUNT(*) INTO :n FROM {core} f WHERE {key};',
                 '  IF (n <> 1) THEN RAISE guard_failed; END IF;',
                 f'  SELECT COUNT(*) INTO :n FROM {saved} b WHERE {old_key};',
                 '  IF (n <> 1) THEN RAISE guard_failed; END IF;',
                 f'  SELECT COUNT(*) INTO :receipt_count FROM {revisions} WHERE REVISION_ID={quote(revision_id)};',
                 f'  SELECT COUNT(*) INTO :audit_count FROM {audit} WHERE AUDIT_ID={quote(audit_id)};',
                 '  IF (receipt_count=1 AND audit_count=1) THEN',
                 f'    SELECT AFTER_DATA INTO :receipt_after FROM {revisions} WHERE REVISION_ID={quote(revision_id)};',
                 f'    SELECT COUNT(*) INTO :n FROM {core} f WHERE {key} AND {same_snapshot("f", "receipt_after")};',
                 '    IF (n <> 1) THEN RAISE guard_failed; END IF; -- Exact replay only; later edits block it.',
                 '  ELSE', '    IF (receipt_count <> 0 OR audit_count <> 0) THEN RAISE guard_failed; END IF;']
        if rollback:
            body += [f'    SELECT COUNT(*) INTO :n FROM {revisions} WHERE REVISION_ID={quote(apply_revision)};',
                     '    IF (n <> 1) THEN RAISE guard_failed; END IF;',
                     f'    SELECT AFTER_DATA INTO :receipt_after FROM {revisions} WHERE REVISION_ID={quote(apply_revision)};',
                     f'    SELECT BEFORE_DATA INTO :backup_receipt FROM {revisions} WHERE REVISION_ID={quote(apply_revision)};',
                     f'    SELECT COUNT(*) INTO :n FROM {saved} b WHERE {old_key} AND {same_snapshot("b", "backup_receipt")};',
                     '    IF (n <> 1) THEN RAISE guard_failed; END IF; -- Do not restore a changed or mismatched backup.',
                     f'    SELECT COUNT(*) INTO :n FROM {core} f WHERE {key} AND {same_snapshot("f", "receipt_after")};',
                     '    IF (n <> 1) THEN RAISE guard_failed; END IF;']
        else:
            expected_dates = ' AND '.join(f'EQUAL_NULL(b.{field},{literal(row["old"][field], field)})' for field in DATE_FIELDS)
            body += [f'    SELECT COUNT(*) INTO :n FROM {saved} b WHERE {old_key} AND {expected_dates};',
                     '    IF (n <> 1) THEN RAISE guard_failed; END IF;']
        body += [f'    SELECT {snapshot("f")} INTO :before_row FROM {core} f WHERE {key};']
        assignments = [f'{field}=' + (f'b.{field}' if rollback else literal(row['new'][field], field))
                       for field in row['changed_fields']]
        assignments.append("UPDATED_AT=CONVERT_TIMEZONE('UTC',CURRENT_TIMESTAMP())::TIMESTAMP_NTZ")
        cas = same_snapshot('f', 'receipt_after') if rollback else ' AND '.join(
            f'EQUAL_NULL(f.{field},b.{field})' for field in (*FIELDS, 'UPDATED_AT'))
        body += [f'    UPDATE {core} AS f SET ' + ', '.join(assignments),
                 f'      FROM {saved} b WHERE {key} AND b.FLOCK_ID=f.FLOCK_ID AND {cas};',
                 '    n := SQLROWCOUNT;', '    IF (n <> 1) THEN RAISE guard_failed; END IF;',
                 f'    SELECT {snapshot("f")} INTO :after_row FROM {core} f WHERE {key};',
                 f'    INSERT INTO {revisions} (REVISION_ID,ENTITY_TYPE,ENTITY_ID,CHANGE_KIND,BUSINESS_AT,RECORDED_AT,RECORDED_BY,REASON,BEFORE_DATA,AFTER_DATA)',
                 f"      SELECT {quote(revision_id)},'FLOCK',{quote(row['flock_id'])},{quote(kind)},NULL,",
                 f"        CONVERT_TIMEZONE('UTC',CURRENT_TIMESTAMP())::TIMESTAMP_NTZ,:actor_id,{quote(reason)},:before_row,:after_row;",
                 '    n := SQLROWCOUNT;', '    IF (n <> 1) THEN RAISE guard_failed; END IF;',
                 f'    INSERT INTO {audit} (AUDIT_ID,ACTOR_USER_ID,ACTOR_EMAIL,ACTION,ENTITY_TYPE,ENTITY_ID,DETAILS,OCCURRED_AT)',
                 f"      SELECT {quote(audit_id)},:actor_id,:actor_email,'UPDATE','FLOCK',{quote(row['flock_id'])},",
                 f"        OBJECT_CONSTRUCT('reason',{quote(reason)},'request_id',{quote(revision_id)},'history_kind',{quote(kind)}),",
                 "        CONVERT_TIMEZONE('UTC',CURRENT_TIMESTAMP());", '    n := SQLROWCOUNT;',
                 '    IF (n <> 1) THEN RAISE guard_failed; END IF;', '  END IF;']
    body += ['  COMMIT;', '  started := FALSE;', f"  RETURN 'Reviewed disposal {direction} completed or already applied';",
             'EXCEPTION', '  WHEN OTHER THEN', '    IF (started) THEN ROLLBACK; END IF;', '    RAISE;', 'END;', '$$;', '']
    return '\n'.join(body)


def verification_sql(rows, *, database='EFNS_DEV'):
    if not re.fullmatch(r'[A-Z][A-Z0-9_]*', database):
        raise ValueError('Unsafe SQL identifier.')
    values = ',\n    '.join('(' + ','.join([quote(r['permit']), quote(r['account_id']), quote(r['flock_id']),
                       literal(r['new']['EST_DISPOSAL'], 'EST_DISPOSAL'), literal(r['new']['DISPOSAL_DATE'], 'DISPOSAL_DATE'),
                       literal(r['new']['BIRDS_DISPOSED'], 'BIRDS_DISPOSED') if 'BIRDS_DISPOSED' in r['changed_fields'] else 'NULL',
                       'TRUE' if 'BIRDS_DISPOSED' in r['changed_fields'] else 'FALSE']) + ')' for r in rows)
    return ("-- Read-only pre-check / post-check. Review ROW_MATCHES, identity and old quantity before any apply.\n"
            'WITH targets (PERMIT_NUMBER,ACCOUNT_ID,EXPECTED_FLOCK_ID,NEW_EST_DISPOSAL,NEW_DISPOSAL_DATE,NEW_BIRDS_DISPOSED,SET_BIRDS) AS (\n'
            f'  SELECT * FROM VALUES\n    {values}\n)\n'
            'SELECT t.*, f.FLOCK_ID, f.EST_DISPOSAL, f.DISPOSAL_DATE, f.BIRDS_DISPOSED, f.UPDATED_AT,\n'
            '  COUNT(f.FLOCK_ID) OVER (PARTITION BY t.PERMIT_NUMBER,t.ACCOUNT_ID) AS ROW_MATCHES,\n'
            '  EQUAL_NULL(f.FLOCK_ID,t.EXPECTED_FLOCK_ID) AS FLOCK_ID_MATCH,\n'
            '  (EQUAL_NULL(f.EST_DISPOSAL,t.NEW_EST_DISPOSAL) AND EQUAL_NULL(f.DISPOSAL_DATE,t.NEW_DISPOSAL_DATE)\n'
            '    AND (NOT t.SET_BIRDS OR EQUAL_NULL(f.BIRDS_DISPOSED,t.NEW_BIRDS_DISPOSED))) AS MATCHES_PROPOSED\n'
            f'FROM targets t LEFT JOIN {database}.CORE.FLOCK f\n'
            '  ON f.PERMIT_NUMBER=t.PERMIT_NUMBER AND f.ACCOUNT_ID=t.ACCOUNT_ID\n'
            'ORDER BY t.PERMIT_NUMBER,f.FLOCK_ID;\n')


def write_csv(path, rows, fields=None):
    if not fields:
        fields = list(rows[0]) if rows else ['no_rows']
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def generate(legacy_path, export_path, output, *, expected_rows=14, actor_id='__SET_APP_USER_ID__', actor_email='__SET_APP_USER_EMAIL__'):
    legacy_path, export_path, output = Path(legacy_path), Path(export_path), Path(output)
    if actor_id != '__SET_APP_USER_ID__':
        UUID(actor_id)
    if actor_email != '__SET_APP_USER_EMAIL__' and ('@' not in actor_email or len(actor_email) > 320):
        raise ValueError('A reviewed app actor email is required.')
    # Never allow an output folder to overwrite either input.
    if any(source.resolve().is_relative_to(output.resolve()) for source in (legacy_path, export_path)):
        raise ValueError('Output directory must not contain the input files.')
    hashes = {source.name: hashlib.sha256(source.read_bytes()).hexdigest() for source in (legacy_path, export_path)}
    legacy, current, bindings = read_inputs(legacy_path, export_path)
    rows, summary, differences, missing, duplicates = reconcile(legacy, current, expected_rows=expected_rows)
    plan_id = hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()[:24]
    summary.update(input_sha256=hashes, plan_id=plan_id, dataverse_hidden_field_bindings=bindings)
    # Validate every SQL document and the input snapshot before writing outputs.
    # A validation failure must not replace half of an existing reviewed plan.
    documents = {name: generate_sql(rows, plan_id, actor_id=actor_id, actor_email=actor_email, rollback=reverse)
                 for name, reverse in [('apply.sql', False), ('rollback.sql', True)]}
    documents.update({name: verification_sql(rows) for name in ('precheck.sql', 'verification.sql')})
    if hashes != {source.name: hashlib.sha256(source.read_bytes()).hexdigest() for source in (legacy_path, export_path)}:
        raise RuntimeError('An input changed while the plan was generated; no outputs written.')
    output.mkdir(parents=True, exist_ok=True)
    flat = []
    for row in rows:
        item = {key: row[key] for key in ('permit', 'account', 'account_id', 'flock_id', 'source_excel_row')}
        item['FLOCK_ID_LOOKUP'] = f"SELECT FLOCK_ID FROM EFNS_DEV.CORE.FLOCK f WHERE {identity(row)}"
        item['changed_fields'] = '|'.join([*row['changed_fields'], 'UPDATED_AT'])
        for field in (*FIELDS, 'UPDATED_AT'):
            item['old_' + field], item['new_' + field] = row['old'][field], row['new'][field]
        flat.append(item)
    write_csv(output/'corrections.csv', flat)
    write_csv(output/'comparison_differences.csv', differences)
    write_csv(output/'unmatched_legacy_rows.csv', missing)
    write_csv(output/'duplicate_permits.csv', duplicates)
    (output/'comparison.json').write_text(json.dumps(summary, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    for name, content in documents.items():
        (output/name).write_text(content, encoding='utf-8')
    if hashes != {source.name: hashlib.sha256(source.read_bytes()).hexdigest() for source in (legacy_path, export_path)}:
        raise RuntimeError('An input changed while the plan was generated; discard and regenerate outputs.')
    return rows, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--legacy', type=Path, required=True)
    parser.add_argument('--flocks', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--expected-rows', type=int, default=14)
    parser.add_argument('--actor-id', default='__SET_APP_USER_ID__')
    parser.add_argument('--actor-email', default='__SET_APP_USER_EMAIL__')
    args = parser.parse_args()
    _, summary = generate(args.legacy, args.flocks, args.output, expected_rows=args.expected_rows,
                          actor_id=args.actor_id, actor_email=args.actor_email)
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
