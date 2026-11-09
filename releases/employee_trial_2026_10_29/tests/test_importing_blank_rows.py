"""Synthetic workbook blanks must not discard invalid populated source rows."""
from io import BytesIO

from openpyxl import Workbook

from data.constants import EIMS_REQUIRED_COLUMNS, EIMS_WORKSHEET_NAME
from data.importing import read_eims_workbook, validate_eims_records


def test_whitespace_rows_are_empty_but_partial_rows_keep_original_excel_numbers():
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = EIMS_WORKSHEET_NAME
    columns = list(EIMS_REQUIRED_COLUMNS) + ['Extra source column']
    for index, column in enumerate(columns, 1):
        sheet.cell(10, index, column)

    def source(row_number, values):
        for column, value in values.items():
            sheet.cell(row_number, columns.index(column) + 1, value)

    source(11, {'Week': '202645', 'Producer #': '001', 'Total': 12})
    source(12, {'Week': ' \t', 'Extra source column': '\n\u00a0'})
    source(13, {'Week': '202645', 'Producer #': ' ', 'Total': 5})
    source(14, {'Week': '202645', 'Producer #': '002', 'Total': 0})
    for row_number in (71, 73, 74):
        source(row_number, {'Extra source column': ' '})
    source(72, {'Week': '202645', 'Producer #': '003', 'Total': 8})
    content = BytesIO()
    workbook.save(content)
    content.seek(0)

    raw = read_eims_workbook(content)
    assert raw.SOURCE_ROW_NUMBER.tolist() == [11, 13, 14, 72]
    assert raw['Producer #'].tolist() == ['001', ' ', '002', '003']
    assert raw.loc[2, 'Total'] == 0
    errors, warnings = validate_eims_records(raw)
    assert errors == ['Excel row 13: Producer # is missing.']
    assert warnings == []
