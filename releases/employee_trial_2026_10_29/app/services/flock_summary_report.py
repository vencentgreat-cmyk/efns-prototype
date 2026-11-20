"""Weekly stock snapshots from the maintained EFC calendar and Status builder."""
import datetime as dt
from decimal import Decimal
import pandas as pd
from data.position_evidence import day, number
from data.quota_types import quota_type_key
from app.services.flock_reports import build_flock_status_report
from app.services.flock_current_report import text

from data.efc_calendar import (INVENTORY_AS_OF_WEEK_DAY, WEEKLY_INVENTORY_CAPTION, synthetic_efc_calendar, efc_weeks, resolve_production_week, default_flock_summary_weeks)


def build_flock_summary_report(flocks,transactions,accounts,facilities,calendar,start_week,end_week,
                               mortality='0.4',quota_type='Egg Production',group_by_producer=False):
    first=resolve_production_week(calendar,start_week);last=resolve_production_week(calendar,end_week)
    if first[0]>last[0]:raise ValueError('Start Week must be on or before End Week.')
    weeks={code:dates for code,dates in efc_weeks(calendar).items() if first[0]<=dates[0]<=last[0]}
    ordered=sorted(weeks)
    if any(weeks[b][0]-weeks[a][1]!=dt.timedelta(days=1) for a,b in zip(ordered,ordered[1:])):
        raise ValueError('The EFC calendar is missing weeks in the selected range.')
    kinds=sorted({'Egg Production',*(quota_type_key(v) or 'Not specified' for v in flocks.get('FLOCK_QUOTA_TYPE',[]) if text(v)!='Special Permit')})
    columns=['Week','Week Start','As-of Date',*(['Reg No','Account'] if group_by_producer else []),'Total Inventory',*kinds]
    owners={str(r['ACCOUNT_ID']):r for r in accounts.to_dict('records')}
    internal=accounts.copy()
    if not internal.empty:internal['ORGANIZATION_NAME']=internal.ACCOUNT_ID.map(str)
    output=[];notes=[WEEKLY_INVENTORY_CAPTION]
    for code in ordered:
        begin,end=weeks[code];groups={}
        for kind in kinds:
            if quota_type!='All' and quota_type_key(quota_type)!=kind:continue
            source=flocks.loc[flocks.get('FLOCK_QUOTA_TYPE',pd.Series(index=flocks.index,dtype=object)).map(lambda value: quota_type_key(value) or 'Not specified').eq(kind)]
            frame,_=build_flock_status_report(source,transactions,internal,facilities,{},end,mortality,'All' if kind=='Not specified' else kind)
            for row in frame.to_dict('records'):
                if row['Permit No']!='Total':continue
                identity=row['Account'];value=number(row['Inventory'])
                groups.setdefault(identity,{})[kind]=value
                if value is None:notes.append('Some flock Inventory values are unavailable; totals sum known inventory only.')
        if not groups:continue
        def combined(values):
            known=[v for v in values if v is not None]
            return sum(known,Decimal(0)) if known else None
        targets=[(identity,values) for identity,values in groups.items()] if group_by_producer else [('',{kind:combined([values.get(kind,Decimal(0)) for values in groups.values()]) for kind in kinds})]
        for identity,values in targets:
            owner=owners.get(identity,{})
            row={'Week':code,'Week Start':begin.isoformat(),'As-of Date':end.isoformat(),**{kind:values.get(kind,Decimal(0)) for kind in kinds}}
            row['Total Inventory']=combined(list(values.values()))
            if group_by_producer:row.update({'Reg No':text(owner.get('REGISTRATION_NUMBER')),'Account':text(owner.get('ORGANIZATION_NAME'))})
            output.append(row)
    result=pd.DataFrame(output,columns=columns,dtype=object)
    result=result.where(result.notna(),'—')
    result.attrs['notes']=list(dict.fromkeys(notes))
    return result
