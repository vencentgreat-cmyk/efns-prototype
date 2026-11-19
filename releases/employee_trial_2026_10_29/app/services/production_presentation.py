"""Pure Production presentation: source Dozens calculations stay unchanged."""
from decimal import Decimal

import pandas as pd

from app.services.production_reports import AMOUNTS, COMPONENTS, production_table_frame
from data.position_evidence import known_sum, number

DOZENS_PER_BOX = 15
BOXES_CAPTION = ('In Boxes: 1 box = 15 dozens; each value is rounded down; '
                 'totals are sums of the rounded values.')
UNITS = ('Dozens', 'Boxes')


def boxes_from_dozens(value):
    """Legacy-verified for Summary, by Producer, Details and Details by Grader.

    Each existing report-row component floors independently; aggregate rows
    sum converted components/rows. Do not floor an aggregate Dozens total.
    Integer ratio arithmetic avoids float/context precision and rounds toward
    negative infinity, matching floor even for a negative synthetic component.
    """
    value = number(value)
    if value is None:
        return None
    numerator, denominator = value.as_integer_ratio()
    return Decimal(numerator // (denominator * DOZENS_PER_BOX))


def _sum(rows, column):
    return known_sum([number(row.get(column)) for row in rows])


def _complete_sum(values):
    return sum(values, Decimal(0)) if all(value is not None for value in values) else None


def production_units_frame(frame, unit='Dozens'):
    """Convert detail rows, then rebuild only their existing aggregate measures."""
    if unit not in UNITS:
        raise ValueError('Unit of Measure must be Dozens or Boxes.')
    if unit == 'Dozens':
        return frame.copy(deep=True)
    rows = frame.to_dict('records')
    components = list(COMPONENTS)
    for row in rows:
        if row['Row Type'] != 'Data':
            continue
        for column in components:
            row[column] = boxes_from_dozens(row.get(column))
        row['J2'] = row['J']  # Internal alias only; every display/export projects it out.
        row['Levy'] = _complete_sum([row[column] for column in components[:8]])
        row['NonLevy'] = _complete_sum([row[column] for column in components[8:]])
        row['Total'] = _complete_sum([row['Levy'], row['NonLevy']])
    data = [row for row in rows if row['Row Type'] == 'Data']
    producer_rows = []
    for row in rows:
        kind = row['Row Type']
        if kind == 'Data':
            producer_rows.append(row)
            continue
        if kind == 'Week Total':
            scoped = [detail for detail in data if detail['Week'] == row['Week']]
        elif kind == 'Producer Total':
            scoped, producer_rows = producer_rows, []
        elif kind in {'Grand Total', 'Grader Total'}:
            scoped = data
        else:
            continue
        for column in AMOUNTS:
            row[column] = _sum(scoped, column)
    result = pd.DataFrame(rows, columns=frame.columns, dtype=object)
    result = result.where(result.notna(), '')
    result.attrs = frame.attrs.copy()
    return result


def production_week_totals(frame):
    """One row for each observed production week; never invent missing weeks."""
    data = frame.loc[frame['Row Type'].eq('Data')].to_dict('records')
    rows = []
    for week in sorted({row['Week'] for row in data}):
        scoped = [row for row in data if row['Week'] == week]
        total = dict.fromkeys(frame.columns, '')
        total.update({'Row Type': 'Week Total', 'Week': week})
        total.update({column: _sum(scoped, column) for column in AMOUNTS})
        rows.append(total)
    return pd.DataFrame(rows, columns=frame.columns, dtype=object).where(lambda f: f.notna(), '')


def production_report_view(frame, unit='Dozens', *, weekly_totals_only=False, include_week_totals=True):
    """Keep existing rows/order; append a weekly block only when requested."""
    result = production_units_frame(frame, unit)
    if result.empty:
        result.attrs['unit'] = unit
        return result
    weekly = production_week_totals(result)
    if weekly_totals_only:
        grand = result.loc[result['Row Type'].isin(['Grand Total', 'Grader Total'])].copy()
        grand['Row Type'] = 'Grand Total'
        result = pd.concat([weekly, grand], ignore_index=True)
    elif include_week_totals and not result['Row Type'].eq('Week Total').any():
        final = result['Row Type'].isin(['Grand Total', 'Grader Total'])
        heading = pd.DataFrame([dict(dict.fromkeys(result.columns, ''), **{'Row Type': 'Week Totals'})], dtype=object)
        result = pd.concat([result.loc[~final], heading, weekly, result.loc[final]], ignore_index=True)
    result.attrs = {**frame.attrs, 'unit': unit, 'weekly_totals_only': weekly_totals_only}
    return result


def production_view_metadata(metadata, unit='Dozens', *, weekly_totals_only=False):
    """Unit/run wording only; retained source diagnostics stay in Dozens."""
    if unit not in UNITS:
        raise ValueError('Unit of Measure must be Dozens or Boxes.')
    result = {**metadata, 'unit': unit}
    result['headers'] = ['In '+unit if line in {'In Dozens', 'In Boxes'} else line
                         for line in metadata['headers']]
    if weekly_totals_only:
        result['headers'] = [*result['headers'], 'Weekly totals only']
    if unit == 'Boxes':
        result['unit_caption'] = BOXES_CAPTION
    return result


def production_csv_frame(frame):
    """CSV keeps its first header row; only Boxes quantity labels gain units."""
    result = production_table_frame(frame)
    if frame.attrs.get('unit', 'Dozens') != 'Boxes':
        return result
    return result.rename(columns={column: column+' (Boxes)' for column in AMOUNTS
                                  if column in result})
