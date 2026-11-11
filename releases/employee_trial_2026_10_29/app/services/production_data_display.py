"""Production Data presentation only: preserve source quantities and row identity."""
import pandas as pd

from app.services.production_reports import COMPONENTS, NEST_FIELDS, production_week
from data.producer_identity import production_identities, text

DETAIL_FIELDS = tuple(dict.fromkeys([*COMPONENTS.values(), *NEST_FIELDS.values(),
    'MARKETING_TYPE', 'HOUSING_SYSTEM', 'EGG_TYPE', 'GRADER_NAME', 'GRADER_ACCOUNT_ID',
    'PRODUCER_ACCOUNT_ID']))


def production_detail_range(records):
    weeks = [week for row in records.to_dict('records') if (week := production_week(row)) is not None]
    return (min(weeks), max(weeks)) if weeks else None


def production_display_records(records, details, accounts):
    """Enrich the selected summary rows one-to-one; never round or recompute totals."""
    result = records.copy()
    if not details.empty:
        if details['PRODUCTION_ID'].isna().any() or details['PRODUCTION_ID'].duplicated().any():
            raise ValueError('Production detail records have missing or duplicate Production IDs.')
        source = details.set_index('PRODUCTION_ID')
        for field in DETAIL_FIELDS:
            if field not in source:
                continue
            values = result['PRODUCTION_ID'].map(source[field])
            result[field] = result[field].combine_first(values) if field in result else values
    owners = {(text(row.get('ACCOUNT_ID')) or '').casefold(): row for row in accounts.to_dict('records')}
    result = production_identities(result)
    labels, graders = [], []
    for row in result.to_dict('records'):
        label = row['PRODUCER_IDENTITY_LABEL']
        if row['PRODUCER_IDENTITY_STATUS'] == 'ACCOUNT_LINKED':
            owner = owners.get((text(row.get('PRODUCER_ACCOUNT_ID')) or '').casefold(), {})
            label = ' · '.join(filter(None, [text(owner.get('ORGANIZATION_NAME')), text(owner.get('REGISTRATION_NUMBER'))]))
            label = label or 'Linked account (details unavailable)'
        labels.append(label)
        grader = owners.get((text(row.get('GRADER_ACCOUNT_ID')) or '').casefold(), {})
        graders.append(text(grader.get('ORGANIZATION_NAME')) or text(row.get('GRADER_NAME')) or '')
    result['PRODUCER_IDENTITY_LABEL'] = pd.Series(labels, index=result.index, dtype=object)
    result['GRADING_STATION'] = pd.Series(graders, index=result.index, dtype=object)
    for label, field in COMPONENTS.items():
        result[label] = result.get(field, pd.Series(index=result.index, dtype=object))
    for label, field in NEST_FIELDS.items():
        if label not in COMPONENTS:
            result[label] = result.get(field, pd.Series(index=result.index, dtype=object))
    return result
