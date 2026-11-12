"""Read-only Facility Detail field labels and null-safe presentation."""
import pandas as pd


FACILITY_DETAIL_FIELDS = (
    ('DETAIL_NAME', 'Name'),
    ('FACILITY_NAME', 'Facility'),
    ('ACCOUNT_NAME', 'Account'),
    ('DETAIL_TYPE', 'Facility Type'),
    ('DATE_INSTALLED', 'Date Installed'),
    ('BIRD_COLOUR', 'Bird Colour'),
    ('WIDTH', 'Width'),
    ('LENGTH', 'Length'),
    ('HEIGHT', 'Height'),
    ('CAGE_BRAND', 'Cage Brand'),
    ('HIGHEST_BIRDS_PER_CAGE', 'Highest # Birds per Cage'),
    ('NUMBER_OF_CAGES', 'Number of Cages'),
    ('BIRDS_HOUSED', 'Birds Housed'),
    ('SQUARE_INCHES', 'Square Inches (W*L)'),
    ('EIMS_FACILITY_DETAIL_ID', 'EIMS Facility Detail ID'),
    ('STATUS', 'Status'),
    ('COMMENTS', 'Comments'),
    ('CREATED_AT', 'Created On'),
)


def facility_detail_value(field, value, *, timestamp_formatter=None):
    """Format stored values only; never infer dimensions, capacity or units."""
    if value is None or pd.isna(value):
        return '—'
    text = str(value)
    if text.strip().casefold() in {'', 'none', 'null', 'nan', 'nat', '<na>'}:
        return '—'
    if field == 'DATE_INSTALLED' and (isinstance(value, str) or hasattr(value, 'isoformat')):
        parsed = pd.to_datetime(value, errors='coerce')
        if not pd.isna(parsed):
            return parsed.date().isoformat()
    if field == 'CREATED_AT' and timestamp_formatter is not None:
        return timestamp_formatter(value)
    return text


def facility_detail_values(record, *, timestamp_formatter=None):
    return {
        label: facility_detail_value(field, record.get(field), timestamp_formatter=timestamp_formatter)
        for field, label in FACILITY_DETAIL_FIELDS
    }


def facility_detail_frame(frame, *, timestamp_formatter=None):
    """A new read-only display frame, retaining source row order and values."""
    return pd.DataFrame(
        [facility_detail_values(row, timestamp_formatter=timestamp_formatter) for row in frame.to_dict('records')],
        columns=[label for _, label in FACILITY_DETAIL_FIELDS],
    )
