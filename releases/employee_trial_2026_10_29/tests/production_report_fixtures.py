"""Read-only SSRS CSV fixture adapter. Inputs are reconstructed display values,
not claimed raw fractional CORE extracts. SSRS Textbox fields remain expected
aggregate assertions, never production-builder inputs.
"""
import csv
import io
from collections import Counter
from decimal import Decimal
from pathlib import Path

import pandas as pd

from app.services.production_reports import COMPONENTS, NEST_FIELDS

ROOT = Path(__file__).parent/'fixtures'/'production_reports'
FILES = {'summary':'EIMSProductionManagementReport.csv',
    'producer':'EIMSProductionManagementReportbyProducer.csv',
    'details':'EIMSProductionManagementDetails.csv',
    'grader':'EIMSProductionManagementDetailsbyGrader.csv'}
MEASURES = ['J2',*[key for key in COMPONENTS if key!='J'],'NonLevy','Levy','Total']


def read_fixture(layout):
    text = (ROOT/FILES[layout]).read_text(encoding='utf-8-sig')
    lines = text.splitlines()
    offset = next(i for i,line in enumerate(lines) if line.startswith('Production_Week,'))
    return [row for row in csv.DictReader(io.StringIO('\n'.join(lines[offset:]))) if row.get('MarketingType')]


def amount(value):
    return Decimal(value.replace(',','')) if value else None


def mock_fixture(layout):
    names = {row['Production_Week']:row['Account_Name'].strip() for name in ('producer','details','grader') for row in read_fixture(name)}
    expected = read_fixture(layout)
    accounts,records={},[]
    for i,row in enumerate(expected):
        registration = row['Registration_Number'] if layout=='summary' else row['Production_Week']
        identity = 'account-'+registration
        accounts[identity] = dict(ACCOUNT_ID=identity,REGISTRATION_NUMBER=registration,
            ORGANIZATION_NAME=names[registration],GRADER_ROLE=False)
        week = int(row.get('Production_Week2') or row.get('Production_Week1'))
        raw = dict(PRODUCTION_ID=f'legacy-{i:04d}',IMPORT_ID=None,PRODUCER_ACCOUNT_ID=identity,
            PRODUCER_NUMBER=registration,SOURCE_WEEK_CODE=week,REPORTING_YEAR=week//100,REPORTING_WEEK=week%100,
            MARKETING_TYPE=row['MarketingType'],EGG_TYPE=row.get('SpecialtyType1'),
            HOUSING_SYSTEM=row.get('HousingSystemType'),EGG_COLOUR=row.get('Colour1'),
            TOTAL=amount(row['Total']))
        for key,field in COMPONENTS.items(): raw[field]=amount(row['J2' if key=='J' else key])
        # The fixture has no nest-run activity. Per-band zeros are synthetic
        # test inputs, not asserted as a raw CORE extract.
        for field in NEST_FIELDS.values(): raw.setdefault(field,Decimal(0))
        grader_name = (row.get('Grading_Station') or '').strip()
        if grader_name:
            grader = 'grader-'+grader_name
            accounts[grader]=dict(ACCOUNT_ID=grader,REGISTRATION_NUMBER='',ORGANIZATION_NAME=grader_name,GRADER_ROLE=True)
            raw.update(GRADER_ACCOUNT_ID=grader,GRADER_NAME=grader_name,GRADER_NUMBER=grader)
        records.append(raw)
    return pd.DataFrame(records),pd.DataFrame(list(accounts.values())),expected


def expected_signature(row,layout):
    reg = row['Registration_Number'] if layout=='summary' else row['Production_Week']
    week = int(row.get('Production_Week2') or row.get('Production_Week1'))
    return (reg,week,row['MarketingType'],*[amount(row[key]) for key in MEASURES])
