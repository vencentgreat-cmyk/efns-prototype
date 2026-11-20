"""Pure EFC calendar validation; offline generation is explicitly synthetic."""
import datetime as dt
import pandas as pd
from data.position_evidence import day, number

INVENTORY_AS_OF_WEEK_DAY = 5  # Python weekday: Saturday; EFC week END, never a sum over time.
WEEKLY_INVENTORY_CAPTION = 'Inventory is as of the last day of each week (Saturday).'


def synthetic_efc_calendar(year):
    """Offline sample only; production resolves dates exclusively from DIM_EFC_DATE."""
    start=dt.date(year,1,1)
    start-=dt.timedelta(days=(start.weekday()+1)%7)
    end=dt.date(year+1,1,1)
    end-=dt.timedelta(days=(end.weekday()+1)%7)
    return pd.DataFrame([dict(DAY=start+dt.timedelta(days=i),EFC_YEAR=year,EFC_WEEK_NUMBER=i//7+1)
                         for i in range((end-start).days)])


def efc_weeks(calendar):
    groups={}
    for row in calendar.to_dict('records'):
        year,week=number(row.get('EFC_YEAR')),number(row.get('EFC_WEEK_NUMBER'))
        date=day(row.get('DAY'))
        if year is None or week is None or date is None or year!=int(year) or week!=int(week) or not 1<=week<=53:
            raise ValueError('EFC calendar contains an invalid reporting week or date.')
        groups.setdefault(int(year)*100+int(week),[]).append(date)
    output={}
    for code,days in groups.items():
        days=sorted(set(days))
        if len(days)!=7 or days[0].weekday()!=6 or days[-1].weekday()!=INVENTORY_AS_OF_WEEK_DAY or (days[-1]-days[0]).days!=6:
            raise ValueError('EFC calendar requires complete Sunday-to-Saturday weeks.')
        output[code]=(days[0],days[-1])
    return output


def resolve_production_week(calendar, code):
    value=number(code)
    if value is None or value!=int(value) or int(value) not in efc_weeks(calendar):
        raise ValueError('Unknown production week. Choose a YYYYWW code in the EFC calendar.')
    return efc_weeks(calendar)[int(value)]


def default_flock_summary_weeks(calendar,today):
    when=day(today);weeks=efc_weeks(calendar)
    current=next((code for code,(start,end) in weeks.items() if when and start<=when<=end),None)
    if current is None:raise ValueError('The EFC calendar does not cover today. Review the calendar before running Flock Summary.')
    first=current//100*100+1
    if first not in weeks:raise ValueError('The EFC calendar is missing week 1 of the current EFC year.')
    return first,min(current,max(code for code in weeks if code//100==current//100))


