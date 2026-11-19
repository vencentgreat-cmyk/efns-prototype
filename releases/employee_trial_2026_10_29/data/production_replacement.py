"""Pure producer-week identity and upload validation; no repository storage access."""
import re
from data.producer_identity import resolve_producer, text
from data.position_evidence import guid, number

BACKUP_TABLE = 'PRODUCTION_REPLACEMENT_BACKUP'
SUMMARY_KEY = '_EFNS_REPLACEMENT_SUMMARY'


def upload_errors(raw, records, technical_errors):
    """All-or-nothing validation; distinct detail rows in a week are permitted."""
    errors = list(technical_errors)
    seen = set()
    ignored = {'PRODUCTION_ID','SOURCE_FILE_ID','RAW_ROW_ID','SOURCE_ROW_NUMBER',
               'MATCH_STATUS','MATCH_METHOD','MATCH_BASIS','PRODUCER_NUMBER'}
    for row in records.to_dict('records'):
        ordinal = row['SOURCE_ROW_NUMBER']
        if not text(row.get('PRODUCER_ACCOUNT_ID')) or row.get('MATCH_STATUS') != 'UNIQUE_MATCHED':
            errors.append(f'Excel row {ordinal}: Producer must match exactly one existing Account before importing.')
        if not re.fullmatch(r'\d{4}(?:0[1-9]|[1-4]\d|5[0-3])', text(row.get('SOURCE_WEEK_CODE')) or ''):
            errors.append(f'Excel row {ordinal}: Week must be a valid six-digit YYYYWW value.')
        business = {k:v for k,v in row.items() if k not in ignored}
        # Numeric equality, not source spelling, determines an exact duplicate.
        fingerprint = tuple((k, None if text(v) is None else v) for k,v in sorted(business.items()))
        if fingerprint in seen:
            errors.append(f'Excel row {ordinal}: Identical production row is duplicated inside this workbook.')
        seen.add(fingerprint)
    if records.empty and not errors:
        errors.append('No valid production rows were found in the workbook.')
    return list(dict.fromkeys(errors))


def production_week(row):
    code = number(row.get('SOURCE_WEEK_CODE'))
    if code is None:
        year, week = number(row.get('REPORTING_YEAR')), number(row.get('REPORTING_WEEK'))
        code = year*100+week if year is not None and week is not None else None
    return int(code) if code is not None and code == code.to_integral_value() and 1 <= int(code)%100 <= 53 else None


def producer_week(row, accounts):
    decision = resolve_producer(row, accounts)
    return guid(decision['account_id']), production_week(row)


