"""Pure EFC calendar validation; offline generation is explicitly synthetic."""
import datetime as dt
import pandas as pd
from data.position_evidence import day, number

INVENTORY_AS_OF_WEEK_DAY = 4  # Python weekday: Friday; staff decision 2026-11-23, Sunday start + 5 days.
EFC_WEEK_END_WEEK_DAY = 5  # Python weekday: Saturday; calendar boundaries are unchanged.
WEEKLY_INVENTORY_CAPTION = 'Inventory is as of Friday of each EFC week (week start + 5 days), or today if Friday is later than today (week in progress).'


def synthetic_efc_calendar(year):
    """Offline sample only; production resolves dates exclusively from DIM_EFC_DATE."""
    start=dt.date(year,1,1)
    start-=dt.timedelta(days=(start.weekday()+1)%7)
    end=dt.date(year+1,1,1)
    end-=dt.timedelta(days=(end.weekday()+1)%7)
    return pd.DataFrame([dict(DAY=start+dt.timedelta(days=i),EFC_YEAR=year,EFC_WEEK_NUMBER=i//7+1)
                         for i in range((end-start).days)])


def _calendar_groups(calendar):
    """Index labels without validating unrelated week contents."""
    groups={}
    for row in calendar.to_dict('records'):
        year,week=number(row.get('EFC_YEAR')),number(row.get('EFC_WEEK_NUMBER'))
        if year is None or week is None or year!=int(year) or week!=int(week) or not 1<=week<=53:
            continue
        groups.setdefault(int(year)*100+int(week),[]).append(day(row.get('DAY')))
    return groups


def _week_code(code):
    value=number(code)
    if value is None or value!=int(value) or not 100001<=value<=999953 or not 1<=int(value)%100<=53:
        raise ValueError('Enter a valid production week in YYYYWW format (week 01 to 53).')
    return int(value)


def _validated_week(groups,code):
    if code not in groups:
        raise ValueError(f'Week {code} is missing from the EFC calendar.')
    values=groups[code]
    days=sorted({value for value in values if value is not None})
    if (None in values or len(days)!=7 or days[0].weekday()!=6
            or days[-1].weekday()!=EFC_WEEK_END_WEEK_DAY or (days[-1]-days[0]).days!=6):
        raise ValueError(f'Week {code} is not a complete Sunday-to-Saturday week in the EFC calendar.')
    return days[0],days[-1]


def efc_weeks(calendar,start_week,end_week):
    """Validate only the requested inclusive range, including its continuity."""
    first,last=_week_code(start_week),_week_code(end_week)
    if first>last:
        raise ValueError('Start Week must be on or before End Week.')
    groups=_calendar_groups(calendar)
    _validated_week(groups,first)
    _validated_week(groups,last)
    codes=sorted(code for code in groups if first<=code<=last)
    output={code:_validated_week(groups,code) for code in codes}
    for previous,current in zip(codes,codes[1:]):
        if previous//100==current//100:
            missing=previous+1 if current!=previous+1 else None
        elif current//100!=previous//100+1 or previous%100 not in {52,53}:
            missing=previous+1 if previous%100<52 else (previous//100+1)*100+1
        else:
            missing=current//100*100+1 if current%100!=1 else None
        if missing is not None:
            raise ValueError(f'Week {missing} is missing from the selected EFC calendar range.')
        if output[current][0]-output[previous][1]!=dt.timedelta(days=1):
            raise ValueError(f'Week {current} has a gap or overlap after Week {previous} in the EFC calendar.')
    return output


def resolve_production_week(calendar, code):
    """A malformed week elsewhere cannot prevent this single-week lookup."""
    return _validated_week(_calendar_groups(calendar),_week_code(code))


def default_flock_summary_weeks(calendar,today):
    when=day(today);groups=_calendar_groups(calendar)
    # Locate the current Sunday-Saturday block from row dates, even if one
    # day is absent. Validate that candidate instead of silently skipping it.
    sunday=when-dt.timedelta(days=(when.weekday()+1)%7) if when else None
    candidates=[code for code,days in groups.items() if when and any(
        value is not None and sunday<=value<=sunday+dt.timedelta(days=6) for value in days)]
    if not candidates:raise ValueError('The EFC calendar does not cover today. Review the calendar before running Flock Summary.')
    for code in candidates:_validated_week(groups,code)
    if len(candidates)!=1:
        raise ValueError('EFC calendar weeks overlap around today: '+', '.join(map(str,sorted(candidates)))+'.')
    current=candidates[0]
    first=current//100*100+1
    # Week 1 is a proposed input, not yet a requested calculation. Validate it
    # only if the user runs a range containing it, so another range stays usable.
    return first,current


