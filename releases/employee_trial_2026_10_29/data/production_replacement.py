"""Pure producer-week identity and upload validation; no repository storage access."""
import re
from data.constants import EIMS_COLUMN_MAPPING, EIMS_NUMERIC_COLUMNS
from data.producer_identity import resolve_producer, text
from data.position_evidence import guid, number

BACKUP_TABLE = 'PRODUCTION_REPLACEMENT_BACKUP'
SUMMARY_KEY = '_EFNS_REPLACEMENT_SUMMARY'

# Quantities only: producer/week/age/row numbers are identities or dimensions.
# Include optional maintained numeric production fields as well as EIMS sizes.
PRODUCTION_QUANTITY_COLUMNS = frozenset(
    EIMS_COLUMN_MAPPING[column] for column in EIMS_NUMERIC_COLUMNS
) | frozenset({'NET_WEIGHT','NET_BOXES','NET_PER_BOX','TOTAL_RECEIVED',
               'REJECTED','LOSS','LEGACY_REJECT_LOSS_TOTAL','TOTAL_ACCEPTED'})
_ROW_IDENTITY_FIELDS = frozenset({'PRODUCTION_ID','SOURCE_FILE_ID','RAW_ROW_ID',
    'SOURCE_ROW_NUMBER','MATCH_STATUS','MATCH_METHOD','MATCH_BASIS','PRODUCER_NUMBER'})


def _all_zero_quantities(row):
    """Blank/zero quantities qualify; malformed numeric text never does."""
    return all(text(row.get(column)) is None or number(row[column]) == 0
               for column in PRODUCTION_QUANTITY_COLUMNS if column in row)


def _row_fingerprint(row, zero):
    # Blank and zero are equivalent only when classifying a zero-only group.
    # Non-zero duplicate equality retains the existing normalized values.
    return tuple((key, 0 if zero and key in PRODUCTION_QUANTITY_COLUMNS else
                  None if text(value) is None else value)
                 for key,value in sorted(row.items()) if key not in _ROW_IDENTITY_FIELDS)


def zero_duplicate_warnings(records):
    """Report all retained source rows, including the first row of each group."""
    groups={}
    for row in records.to_dict('records'):
        if _all_zero_quantities(row):
            groups.setdefault(_row_fingerprint(row,True),[]).append(int(row['SOURCE_ROW_NUMBER']))
    duplicates=[rows for rows in groups.values() if len(rows)>1]
    if not duplicates:return []
    rows=sorted(ordinal for group in duplicates for ordinal in group)
    grouping=f' in {len(duplicates)} groups' if len(duplicates)>1 else ''
    return [f'{len(rows)} identical all-zero rows{grouping} were kept '
            f'(Excel rows {", ".join(map(str,rows))}).']


def upload_errors(raw, records, technical_errors):
    """All-or-nothing validation; distinct detail rows in a week are permitted."""
    errors = list(technical_errors)
    seen = set()
    for row in records.to_dict('records'):
        ordinal = row['SOURCE_ROW_NUMBER']
        if not text(row.get('PRODUCER_ACCOUNT_ID')) or row.get('MATCH_STATUS') != 'UNIQUE_MATCHED':
            errors.append(f'Excel row {ordinal}: Producer must match exactly one existing Account before importing.')
        if not re.fullmatch(r'\d{4}(?:0[1-9]|[1-4]\d|5[0-3])', text(row.get('SOURCE_WEEK_CODE')) or ''):
            errors.append(f'Excel row {ordinal}: Week must be a valid six-digit YYYYWW value.')
        # Numeric equality, not source spelling, determines an exact duplicate.
        zero = _all_zero_quantities(row)
        fingerprint = _row_fingerprint(row,zero)
        if fingerprint in seen and not zero:
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


