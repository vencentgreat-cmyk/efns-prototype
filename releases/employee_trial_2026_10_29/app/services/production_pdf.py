"""Legacy Production PDF presentation only; source rows and measures stay intact."""
from app.services.production_reports import AMOUNTS, PRODUCTION_CAPTION

PRODUCTION_PDF_REPORTS = frozenset({'production-management-summary', 'production-management-details'})
PDF_COLUMNS = ('Reg No', 'Marketing Type', 'Specialty', 'Housing System', 'Colour',
               *(column for column in AMOUNTS if column != 'J2'))
PDF_LABELS = {'Reg No': 'REG#', 'Marketing Type': 'Type', 'Specialty': 'Specialty Type',
              'NonLevy': 'Non Levy'}
MIN_PRODUCTION_FONT = 6.5


def uses_production_layout(report_id, columns):
    return report_id in PRODUCTION_PDF_REPORTS and set((*PDF_COLUMNS, 'Row Type', 'Week')).issubset(columns)


def production_pdf_rows(rows):
    """Project CSV display strings, retaining order and inserting week headings.

    Details retains its producer/week order, so a week heading can repeat when
    the producer changes. No value is summed, rounded or recomputed here.
    """
    positions = {column: index for index, column in enumerate(rows[0])}
    result = [[PDF_LABELS.get(column, column) for column in PDF_COLUMNS]]
    weeks, totals = [], []
    previous = None
    for row in rows[1:]:
        week = row[positions['Week']]
        if week and week != previous:
            weeks.append(len(result))
            result.append(['Production Week: ' + week] + [''] * (len(PDF_COLUMNS) - 1))
            previous = week
        values = [row[positions[column]] for column in PDF_COLUMNS]
        if row[positions['Row Type']] != 'Data':
            totals.append(len(result))
            values[:5] = [row[positions['Row Type']], '', '', '', '']
        result.append(values)
    return result, weeks, totals


def production_table_layout(rows, available_width):
    """Measure every numeric cell in bold; numbers must fit without wrapping."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    for size in (8, 7.5, 7, MIN_PRODUCTION_FONT):
        minimum = [30, 18, 37, 40, 30]
        minimum[0] = max(minimum[0], max((stringWidth(row[0], 'Helvetica-Bold', size) + 5
            for row in rows[1:] if row[0].isdecimal()), default=0))
        for col in range(5, len(PDF_COLUMNS)):
            minimum.append(max(size + 4, max((stringWidth(row[col], 'Helvetica-Bold', size)
                for row in rows[1:]), default=0) + 5))
        if sum(minimum) <= available_width:
            # Prefer room for descriptive headers/text once atomic numbers fit.
            extra = available_width - sum(minimum)
            weights = [1, 1, 2, 2, 1] + [0.25] * (len(PDF_COLUMNS) - 5)
            return size, [width + extra * weight / sum(weights) for width, weight in zip(minimum, weights)]
    return None
