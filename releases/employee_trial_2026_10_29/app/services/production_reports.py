"""Pure Production Management projections in dozens; source rows remain immutable."""
from decimal import Decimal, ROUND_HALF_UP
import re

import pandas as pd

from data.producer_identity import production_identities, text
from data.position_evidence import number, guid, known_sum
from data.source_scope import scope_production

MARKETING_TYPES = {'Broiler Breeder':'BB','Hatchery':'HA','Leghorn Breeder':'LB',
                   'Regulated':'RE','Unregulated':'UN'}
COMPONENTS = dict(zip(['J','XL','L','M','S','PW','B','C','NR','CR','OL','ON','RJ','LK','FG','FC'],
    ['JUMBO','EXTRA_LARGE','LARGE','MEDIUM','SMALL','PEEWEE','GRADE_B','GRADE_C','NEST_RUN','CRACKS',
     'OTHER_LEVIABLE','OTHER_NON_LEVIABLE','REJECTS','LEAKERS','FARM_GATE_SALES','ON_FARM_CONSUMPTION']))
AMOUNTS = ['J','J2',*[key for key in COMPONENTS if key != 'J'],'NonLevy','Levy','Total']
NEST_FIELDS = {'NR':'NEST_RUN', **{f'NR{n}':f'NEST_RUN_{n}_PLUS' for n in range(25,16,-1)},
               'FG':'FARM_GATE_SALES','FC':'ON_FARM_CONSUMPTION'}
DISPLAY = ['Row Type','Week','Reg No','Account Name','Marketing Type','Specialty','Housing System','Colour','Grading Station']


def safe_text(value):
    return text(value) or ''


def validate_week(value):
    value = safe_text(value)
    numeric = number(value)
    if numeric is not None and numeric == numeric.to_integral_value():
        value = str(int(numeric))
    if not re.fullmatch(r'\d{6}',value) or not 1 <= int(value[-2:]) <= 53:
        raise ValueError('Week must be YYYYWW with week 01–53.')
    return int(value)


def week_range(start,end):
    start,end = validate_week(start),validate_week(end)
    if start > end:
        raise ValueError('Start Week must be on or before End Week.')
    return start,end


def production_week(row):
    value = safe_text(row.get('SOURCE_WEEK_CODE'))
    if re.fullmatch(r'\d{4}-W\d{2}',value):
        value = value.replace('-W','')
    if value:
        try: return validate_week(value)
        except ValueError: return None
    year,week = number(row.get('REPORTING_YEAR')),number(row.get('REPORTING_WEEK'))
    if year is None or week is None or year != int(year) or week != int(week):
        return None
    try: return validate_week(f'{int(year):04d}{int(week):02d}')
    except ValueError: return None


def _rounded(value):
    value = number(value)
    return value.quantize(Decimal(1),rounding=ROUND_HALF_UP) if value is not None else None


def _complete_sum(values):
    return sum(values,Decimal(0)) if all(value is not None for value in values) else None


def _order(value):
    value = safe_text(value)
    return (0,Decimal(value)) if value.isdecimal() else (1,value.casefold()) if value else (2,'')


def _code(value):
    value = safe_text(value)
    return MARKETING_TYPES.get(value,value.upper())


def prepare_production(records,accounts,start_week,end_week,marketing_types=None,*,account_ids=None,grader_key=None):
    """Round components per stored row, then derive totals; J2 is display-only.

    Fractional rounding is PROVISIONAL HALF_UP: CSVs prove integer component
    arithmetic but do not supply raw fractional CORE values. Stored TOTAL is
    reconciled and reported, never used to override displayed component sums.
    """
    start,end = week_range(start_week,end_week)
    parents = accounts.to_dict('records')
    ids = [guid(row.get('ACCOUNT_ID')) for row in parents]
    if None in ids or len(set(ids)) != len(ids):
        raise ValueError('Missing or duplicate Account identity.')
    owners = dict(zip(ids,parents))
    if not records.empty and (records.PRODUCTION_ID.isna().any() or records.PRODUCTION_ID.duplicated().any()):
        raise ValueError('Missing or duplicate Production ID.')
    source = scope_production(records)
    source = source.loc[source.SOURCE_SCOPE.ne('DEV test data')].copy()
    source['PRODUCER_ACCOUNT_NAME'] = source.get('PRODUCER_ACCOUNT_ID',pd.Series(index=source.index,dtype=object)).map(lambda value:safe_text(owners.get(guid(value),{}).get('ORGANIZATION_NAME')))
    source = production_identities(source)
    grader_source = source.copy()
    grader_source['PRODUCER_ACCOUNT_ID'] = source.get('GRADER_ACCOUNT_ID',pd.Series(index=source.index,dtype=object))
    grader_source['PRODUCER_NUMBER'] = source.get('GRADER_NUMBER',pd.Series(index=source.index,dtype=object))
    grader_source['PRODUCER_ACCOUNT_NAME'] = source.get('GRADER_NAME',pd.Series(index=source.index,dtype=object))
    graders = production_identities(grader_source)
    selected = {_code(value) for value in marketing_types} if marketing_types is not None else None
    if selected == set(MARKETING_TYPES.values()):
        selected = None  # All legacy types: retain unrecognized/blank stored codes with a note.
    selected_accounts = {guid(value) for value in account_ids} if account_ids is not None else None
    rows,notes = [],[]
    for (_,raw),(_,grader_identity) in zip(source.iterrows(),graders.iterrows()):
        row = raw.to_dict()
        week = production_week(row)
        producer = owners.get(guid(row.get('PRODUCER_ACCOUNT_ID')), {})
        grader = owners.get(guid(row.get('GRADER_ACCOUNT_ID')), {})
        markers = [row.get(field) for field in ('PRODUCTION_ID','PRODUCER_NUMBER','GRADER_NUMBER','SOURCE_TYPE','IMPORT_ID')]
        markers += [parent.get(field) for parent in (producer,grader) for field in ('ORGANIZATION_NAME','REGISTRATION_NUMBER')]
        if any(safe_text(value).upper().startswith('DEV_TEST') for value in markers):
            continue
        if week is None:
            notes.append(f"{safe_text(row.get('PRODUCTION_ID'))}: invalid/unknown Week excluded")
            continue
        kind = _code(row.get('MARKETING_TYPE'))
        if not start <= week <= end or (selected is not None and kind not in selected):
            continue
        if selected_accounts is not None and guid(row.get('PRODUCER_ACCOUNT_ID')) not in selected_accounts:
            continue
        if grader_key is not None and grader_identity['PRODUCER_IDENTITY_KEY'] != grader_key:
            continue
        if kind not in MARKETING_TYPES.values():
            notes.append(f"{safe_text(row.get('PRODUCTION_ID'))}: unrecognized/blank Marketing Type retained in All Types scope")
        if kind in {'BB','HA'}:
            notes.append('PROVISIONAL type mapping: BB = Broiler Breeder; HA = Hatchery. These codes are not present in the supplied CSVs.')
        measures = {key:_rounded(row.get(field)) for key,field in COMPONENTS.items()}
        measures['J2'] = measures['J']
        measures['Levy'] = _complete_sum([measures[key] for key in list(COMPONENTS)[:8]])
        measures['NonLevy'] = _complete_sum([measures[key] for key in list(COMPONENTS)[8:]])
        measures['Total'] = _complete_sum([measures['Levy'],measures['NonLevy']])
        stored = number(row.get('TOTAL'))
        if stored is not None and measures['Total'] is not None and stored != measures['Total']:
            notes.append(f"{safe_text(row.get('PRODUCTION_ID'))}: stored TOTAL {stored} versus displayed {measures['Total']} (difference {measures['Total']-stored})")
        if any(measures[key] is None for key in COMPONENTS):
            notes.append(f"{safe_text(row.get('PRODUCTION_ID'))}: unknown components; totals sum known displayed values only")
        record = dict(measures, **{'Row Type':'Data','Week':week,
            'Reg No':safe_text(producer.get('REGISTRATION_NUMBER')) or safe_text(row.get('PRODUCER_NUMBER')),
            'Account Name':safe_text(producer.get('ORGANIZATION_NAME')) if guid(row.get('PRODUCER_ACCOUNT_ID')) else row['PRODUCER_IDENTITY_LABEL'],
            'Marketing Type':kind,'Specialty':safe_text(row.get('EGG_TYPE')),
            'Housing System':safe_text(row.get('HOUSING_SYSTEM')),'Colour':safe_text(row.get('EGG_COLOUR')),
            'Grading Station':safe_text(grader.get('ORGANIZATION_NAME')) or safe_text(row.get('GRADER_NAME')),
            '_producer':row['PRODUCER_IDENTITY_KEY'],'_account':guid(row.get('PRODUCER_ACCOUNT_ID')),
            '_grader':grader_identity['PRODUCER_IDENTITY_KEY'],'_grader_account':guid(row.get('GRADER_ACCOUNT_ID')),
            '_id':safe_text(row.get('PRODUCTION_ID'))})
        record.update({key:_rounded(row.get(field)) for key,field in NEST_FIELDS.items()})
        rows.append(record)
    return rows, {'notes':list(dict.fromkeys(notes)),
        'headers':[f'Production Week: {start} to {end}','Type: '+', '.join(marketing_types if marketing_types is not None else MARKETING_TYPES),'In Dozens'],
        'rounding':'PROVISIONAL: round each stored component HALF_UP to whole dozens; sum displayed components; J2 excluded from Levy.'}


def _total(rows,label,keys=AMOUNTS,**fields):
    return dict({key:known_sum([row.get(key) for row in rows]) for key in keys}, **{'Row Type':label}, **fields)


def _frame(rows,columns):
    frame = pd.DataFrame(rows,columns=columns,dtype=object)
    return frame.where(frame.notna(),'')


def production_grader_options(records,accounts,start_week,end_week):
    rows,_ = prepare_production(records,accounts,start_week,end_week)
    return {row['_grader']:row['Grading Station'] or row['_grader'] for row in rows}


def build_production_report(records,accounts,start_week,end_week,marketing_types=None,*,
                            layout='summary',account_ids=None,grader_key=None):
    """Preserve stored detail rows, including repeated visible keys, like the CSVs."""
    if layout not in {'summary','producer','details','grader'}:
        raise ValueError('Unknown Production Management layout.')
    if layout == 'grader' and not grader_key:
        raise ValueError('Select a Grading Station before running this report.')
    rows,meta = prepare_production(records,accounts,start_week,end_week,marketing_types,
        account_ids=account_ids,grader_key=grader_key)
    if layout == 'grader' and rows:
        meta['headers'].append('Grading Station: '+rows[0]['Grading Station'])
        meta['headers'].append('Account selection: '+('All Accounts' if account_ids is None else str(len(account_ids))+' selected'))
    output=[]
    if layout == 'summary':
        for week in sorted({row['Week'] for row in rows}):
            scoped = sorted([row for row in rows if row['Week']==week],key=lambda row:(_order(row['Reg No']),row['_producer'],row['Marketing Type'],row['Specialty'],row['Housing System'],row['Colour'],row['_id']))
            output.append(_total(scoped,'Week Total',Week=week))
            output.extend(scoped)
    else:
        groups = {}
        for row in rows: groups.setdefault(row['_producer'],[]).append(row)
        for identity in sorted(groups,key=lambda key:(_order(groups[key][0]['Reg No']),key)):
            scoped = sorted(groups[identity],key=lambda row:(row['Week'],row['Marketing Type'],row['Grading Station'],row['_id']))
            if layout == 'grader':
                output.append({'Row Type':'Producer Header','Reg No':scoped[0]['Reg No'],'Account Name':scoped[0]['Account Name']})
            output.extend(scoped)
            if layout == 'producer':
                output.append(_total(scoped,'Producer Total',**{'Reg No':scoped[0]['Reg No'],'Account Name':scoped[0]['Account Name']}))
    if rows:
        output.append(_total(rows,'Grader Total' if layout=='grader' else 'Grand Total'))
    return _frame(output,[*DISPLAY,*AMOUNTS]),meta


def build_nest_run_report(records,accounts,year,start_week,end_week):
    start,end = week_range(start_week,end_week)
    if start//100 != int(year) or end//100 != int(year):
        raise ValueError('Start and End Week must belong to the selected Year.')
    rows,meta = prepare_production(records,accounts,start,end)
    # PROVISIONAL inclusion: observed nest-run/farm activity OR a non-RE/non-UN
    # marketing type, retaining zero-valued Leghorn Breeder rows in the screenshot.
    rows = [row for row in rows if row['Marketing Type'] not in {'RE','UN',''} or
            any(row.get(key) is not None and row[key] != 0 for key in NEST_FIELDS)]
    groups={}
    for row in rows: groups.setdefault((row['Marketing Type'],row['Week'],row['_producer']),[]).append(row)
    details = [dict(_total(group,'Data',keys=NEST_FIELDS),**{'Marketing Type':kind,'Week':week,
        'Reg No':group[0]['Reg No'],'Account Name':group[0]['Account Name']}) for (kind,week,_),group in groups.items()]
    output=[]
    for kind,week in sorted({(row['Marketing Type'],row['Week']) for row in details}):
        scoped = sorted([row for row in details if row['Marketing Type']==kind and row['Week']==week],key=lambda row:_order(row['Reg No']))
        output.extend(scoped)
        output.append(_total(scoped,'Week Total',keys=NEST_FIELDS,**{'Marketing Type':kind,'Week':week}))
    if details: output.append(_total(details,'Grand Total',keys=NEST_FIELDS))
    meta['notes'].append('PROVISIONAL Nest Run inclusion: non-zero NR/NR25–NR17/FG/FC activity, or marketing type other than Regulated/Unregulated; weeks without records are absent.')
    return _frame(output,['Row Type','Marketing Type','Week','Reg No','Account Name',*NEST_FIELDS]),meta
