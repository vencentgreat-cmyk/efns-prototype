"""Legacy Production PDF presentation only; source rows and measures stay intact."""
import re

from app.services.production_reports import AMOUNTS, PRODUCTION_CAPTION

PRODUCTION_PDF_REPORTS = frozenset({'production-management-summary', 'production-management-details'})
PDF_COLUMNS = ('Reg No', 'Marketing Type', 'Specialty', 'Housing System', 'Colour',
               *(column for column in AMOUNTS if column != 'J2'))
PDF_LABELS = {'Reg No': 'REG#', 'Marketing Type': 'Type', 'Specialty': 'Specialty Type',
              'NonLevy': 'Non Levy'}
MIN_PRODUCTION_FONT = 6.5


def production_pdf_notes(lines):
    """Keep the existing summary, without the XLSX's per-record appendix or IDs."""
    result = []
    for line in lines:
        if line.startswith('Rounding differences:'):
            continue
        line = line.removeprefix('Rounding summary: ')
        line = re.sub(r'\b[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}\b',
                      'source record', line, flags=re.IGNORECASE)
        if line not in result:
            result.append(line)
    return result


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
    """Fit atomic numbers, header words and housing values on landscape Letter."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    for size in (8, 7.5, 7, MIN_PRODUCTION_FONT):
        minimum = []
        for col in range(len(PDF_COLUMNS)):
            atoms = rows[0][col].split()
            for row in rows[1:]:
                if col < 5:
                    # Week headings and total labels span multiple columns.
                    if row[0].startswith('Production Week:') or not any(row[1:5]):
                        continue
                    atoms.extend(row[col].split())
                else:
                    atoms.append(row[col])
            if col == 3:
                atoms.extend(('Conventional', 'Enrichable', 'Free Run'))
            minimum.append(max((stringWidth(atom, 'Helvetica-Bold', size)
                                for atom in atoms), default=0) + 5)
        if sum(minimum) <= available_width:
            # Prefer room for descriptive headers/text once atomic numbers fit.
            extra = available_width - sum(minimum)
            weights = [1, 1, 2, 2, 1] + [0.25] * (len(PDF_COLUMNS) - 5)
            return size, [width + extra * weight / sum(weights) for width, weight in zip(minimum, weights)]
    return None
