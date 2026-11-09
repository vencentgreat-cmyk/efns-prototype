"""Evidence-scoped source labels; SOURCE_TYPE is not authenticity evidence."""
import json
from pathlib import Path

import pandas as pd

ALL_DEV = 'All DEV records (mixed sources)'
UNKNOWN = 'Unclassified source'
PROVENANCE = json.loads((Path(__file__).resolve().parents[1] / 'config/source_provenance.json').read_text(encoding='utf-8'))
SOURCE_SCOPES = (ALL_DEV, 'Confirmed historical package', 'Archived workbook; business scope unconfirmed', 'DEV test data', UNKNOWN)


def scope_production(frame, scope=ALL_DEV):
    if scope not in SOURCE_SCOPES:
        raise ValueError('Unknown production source scope.')
    result = frame.copy()
    imports = result.get('IMPORT_ID', pd.Series(None,index=result.index,dtype=object))
    result['SOURCE_SCOPE'] = imports.map(PROVENANCE['batches']).fillna(UNKNOWN)
    return result if scope == ALL_DEV else result.loc[result.SOURCE_SCOPE == scope].copy()
