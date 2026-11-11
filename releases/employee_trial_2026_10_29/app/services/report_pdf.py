"""Presentation-only SSRS-style PDFs with explicit per-report quantity formats."""
import csv
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from io import BytesIO, StringIO
from pathlib import Path
import re
from zoneinfo import ZoneInfo

import pandas as pd

from app.services.printable_form_text import FORM_BLUE

MAX_PDF_ROWS = 5000
MIN_FONT_SIZE = 7
ROW_LIMIT_MESSAGE = 'PDF export is limited to 5,000 rows. Use CSV or XLSX for this report.'
MISSING = re.compile(r'(?<!\w)(?:None|nan|NaT|<NA>)(?!\w)', re.IGNORECASE)
NUMERIC = re.compile(r'^[+-]?(?:\d[\d,]*(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?%?$')
QUANTITY = re.compile(r'^[+-]?(?:\d+(?:\.\d*)?|\.\d+|\d{1,3}(?:,\d{3})+(?:\.\d*)?)(?:[eE][+-]?\d+)?$')

# Exact exported column labels, keyed by catalog report ID. Do not infer from
# dtype or a column-name substring: years, ages, registration/permit numbers,
# dates, percentages, phones and IDs must never receive quantity formatting.
PRODUCTION_QUANTITIES = ('J','J2','XL','L','M','S','PW','B','C','NR','CR','OL','ON','RJ','LK','FG','FC','NonLevy','Levy','Total')
NEST_RUN_QUANTITIES = ('NR','NR25','NR24','NR23','NR22','NR21','NR20','NR19','NR18','NR17','FG','FC')
QUANTITY_COLUMNS_BY_REPORT = {
    'producers-over-quota': ('Inventory',),
    'production-management-summary': PRODUCTION_QUANTITIES,
    'production-management-producer': PRODUCTION_QUANTITIES,
    'production-management-details': PRODUCTION_QUANTITIES,
    'production-management-grader': PRODUCTION_QUANTITIES,
    'production-nest-run': NEST_RUN_QUANTITIES,
    'quota-transactions': ('Bird Count',),
    'quota-leases': ('Price','Bird Count'),
    'quota-leases-by-end-date': ('Price','Bird Count'),
    'quota-history': ('Bird Count','Quota Count Adjust','Running Balance','Current Quota'),
    'quota-summary': ('Issuance',),
    'quota-summary-details': ('Account Total','Quota Bird Count'),
    'flock-status': ('Sold','Inventory','Quota','Up. Flocks'),
    'flock-status-producer': ('Sold','Inventory','Quota','Up. Flocks'),
    'flock-age': ('Inventory','Quota','Up. Flocks'),
    'flock-current': ('Counted','Inventory','Up. Flocks'),
    'flock-current-producer': ('Counted','Inventory','Up. Flocks'),
    'flock-salmonella-schedule': ('Inventory',),
    'scheduled-flock-placements': ('Inventory','Quota','Total Producers','Total Flocks','Total Birds'),
    'flocks-counted': ('Quota','Birds Counted'),
    'flocks-needing-counts': ('Bird Count',),
    'flock-disposals': ('Quota','Placed','Disposed'),
    'salmonella-report': ('Number of Samples',),
    'custom-builder': ('Bird Count','Quantity','Quota Count','Price','Number of Samples','Total Received',
        'Total Accepted','Source Total','Flock record count','Record count','Source Total known count','Source Total missing count'),
    # These retain their specialized, already-established legacy form layouts.
    'license-application': (),
    'flock-permit': (),
    'salmonella-form': (),
}

SUMMARY_QUANTITY_COLUMNS_BY_REPORT = {
    'producers-over-quota': ('Inventory Birds', 'NFPMC Allocation', 'Issuance for Province', 'Producers with Quota'),
}


def pdf_summary_lines(summary, report_id):
    """Presentation-only summary quantities; percentages/identifiers stay exact."""
    allowed = SUMMARY_QUANTITY_COLUMNS_BY_REPORT.get(report_id, ())
    labels = ('Inventory Birds', 'NFPMC Allocation', 'Provincial Utilization',
              'Issuance for Province', 'Producers with Quota')
    return [label + ': ' + (group_quantity(display_text(summary.get(label)))
            if label in allowed else display_text(summary.get(label))) for label in labels]


class PDFExportError(ValueError):
    """A safe user-facing PDF export limitation."""


def ensure_pdf_row_limit(count):
    if count > MAX_PDF_ROWS:
        raise PDFExportError(ROW_LIMIT_MESSAGE)


def display_text(value):
    if value is None:
        return ''
    if not isinstance(value, (str, list, tuple, dict)) and pd.isna(value):
        return ''
    return MISSING.sub('', str(value)).strip()


def csv_display_rows(frame):
    """Use pandas' CSV text, preserving precision, leading zeros and column order.

    No numeric conversion, rounding, aggregation or mutation. Spreadsheet-only
    formula escaping is unnecessary in a PDF, so text stays as displayed.
    """
    if not len(frame.columns):
        return []
    return [[display_text(cell) for cell in row]
            for row in csv.reader(StringIO(frame.to_csv(index=False))) ]


def group_quantity(value):
    """Group exact decimal text without float conversion or fractional rounding."""
    if not QUANTITY.fullmatch(value):
        return value
    try:
        number=Decimal(value.replace(',',''))
    except InvalidOperation:
        return value
    if not number.is_finite():
        return value
    grouped=format(number,',f')
    if number==number.to_integral_value():
        grouped=grouped.partition('.')[0]
    return '+'+grouped if value.startswith('+') else grouped


def pdf_display_rows(frame,report_id=None):
    """Change only explicitly allowlisted PDF cells; never mutate the frame."""
    rows=csv_display_rows(frame)
    if not rows:
        return rows
    allowed=QUANTITY_COLUMNS_BY_REPORT.get(report_id,())
    positions=[index for index,column in enumerate(rows[0]) if column in allowed]
    for row in rows[1:]:
        for index in positions:
            row[index]=group_quantity(row[index])
    return rows


def is_total_row(headers, values):
    labels = {'row type','account','account name','permit no','reg no','registration number','label'}
    for index, value in enumerate(values):
        text = display_text(value)
        if index == 0 or display_text(headers[index]).casefold() in labels:
            if text.casefold() in {'total','totals','subtotal','account total','quota total',
                'grand total','producer total','week total','grader total','total bird count'} or text.startswith('Producers:'):
                return True
    return False


def note_lines(frame, notes=None):
    def flatten(value):
        if isinstance(value, pd.DataFrame):
            for row in csv_display_rows(value)[1:]:
                yield ': '.join(filter(None,row))
        elif isinstance(value, dict):
            for key in ('notes','record_notes','Notes'):
                if key in value:yield from flatten(value[key])
        elif isinstance(value,(tuple,list)):
            for item in value:yield from flatten(item)
        else:
            text=display_text(value)
            if text:yield text
    return list(dict.fromkeys([*flatten(frame.attrs.get('notes',[])),*flatten(notes)]))


def identifier_cell(header, value):
    """Custom builder IDs/keys and GUIDs are atomic display values, not prose."""
    if not value or re.search(r'\s', value) or NUMERIC.fullmatch(value):
        return False
    return (header.casefold().endswith((' id', ' key', ' number', ' no')) or
            bool(re.fullmatch(r'[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}', value)))


def table_layout(rows, available_width, *, keep_identifiers=False):
    """Fit every column, wrapping text and preserving a minimum 7pt font."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    columns=len(rows[0])
    # A bounded sample avoids measuring millions of strings; all actual cells
    # still wrap inside their assigned widths when the table is rendered.
    sample=rows[:101]+rows[-1:]
    identifier_rows=[(row,'Helvetica-Bold' if is_total_row(rows[0],row) else 'Helvetica')
                     for row in rows[1:]] if keep_identifiers else []
    for size in (10,9,8,MIN_FONT_SIZE):
        desired=[]
        minimum=[]
        essential=[]
        for col in range(columns):
            texts=[row[col] for row in sample]
            measured=sorted(stringWidth(line[:300],'Helvetica',size) for text in texts for line in (text.splitlines() or ['']))
            preferred=measured[min(len(measured)-1,int(len(measured)*.85))] if measured else 0
            header_word=max((stringWidth(word,'Helvetica-Bold',size) for word in rows[0][col].split()),default=0)
            widest_char=max((stringWidth(char,'Helvetica-Bold',size) for text in texts for char in set(text[:300])),default=size)
            # Do not break identifiers such as week codes or numeric totals into
            # separate lines. Check all numeric cells, including sparse outliers.
            numeric_width=max((stringWidth(row[col],'Helvetica-Bold',size) for row in rows[1:] if NUMERIC.fullmatch(row[col])),default=0)+5
            identifier_width=max((stringWidth(row[col],font,size) for row,font in identifier_rows
                if identifier_cell(rows[0][col],row[col])),default=0)+5
            required=max(size+4,widest_char+5,numeric_width,identifier_width)
            essential.append(required)
            word_width=max((stringWidth(word,'Helvetica-Bold',size) for text in texts for word in text.split()),default=0)+5
            minimum.append(max(required,min(28,word_width),header_word+5 if keep_identifiers else 0))
            desired.append(max(minimum[-1],22,min(150,max(header_word,preferred)+7)))
        if (sum(minimum)<=available_width and sum(desired)<=available_width*1.1) or size==MIN_FONT_SIZE:
            break
    if sum(minimum)>available_width:
        minimum=essential
    if sum(minimum)>available_width:
        raise PDFExportError('The columns and numeric values cannot fit legibly on Letter paper. Use CSV or XLSX.')
    if sum(desired)<=available_width:
        widths=[value*available_width/sum(desired) for value in desired]
    else:
        extra=available_width-sum(minimum)
        weights=[max(1,w-m) for w,m in zip(desired,minimum)]
        widths=[m+extra*w/sum(weights) for m,w in zip(minimum,weights)]
    return size,widths


def render_report_pdf(title, subtitle_lines, frame, notes=None, *, generated_at=None, report_id=None):
    """Render the export frame with PDF-only quantity grouping. No repository access."""
    ensure_pdf_row_limit(len(frame))
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_RIGHT
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.platypus import Paragraph, Spacer, LongTable, TableStyle
    from xml.sax.saxutils import escape

    when=generated_at or datetime.now(timezone.utc)
    if when.tzinfo is None:
        raise ValueError('PDF generation time must include a timezone.')
    timestamp=when.astimezone(ZoneInfo('America/Halifax')).strftime('%Y-%m-%d %H:%M:%S %Z')+' (America/Halifax)'
    title=display_text(title)
    subtitles=[display_text(value) for value in ([subtitle_lines] if isinstance(subtitle_lines,str) else subtitle_lines or []) if display_text(value)]
    rows=pdf_display_rows(frame,report_id)
    keep_identifiers=report_id=='custom-builder'
    pagesize=landscape(letter) if len(frame.columns)>7 else letter
    layout=None
    if rows:
        try:
            layout=table_layout(rows,pagesize[0]-48,keep_identifiers=keep_identifiers)
        except PDFExportError:
            if not keep_identifiers or pagesize!=letter:
                raise
            pagesize=landscape(letter)
            layout=table_layout(rows,pagesize[0]-48,keep_identifiers=True)
    page_width,page_height=pagesize
    available=page_width-48
    title_style=ParagraphStyle('report-title',fontName='Helvetica-Bold',fontSize=14,leading=17)
    parameter_style=ParagraphStyle('parameters',fontName='Helvetica',fontSize=8,leading=10)
    def paragraph(value,style):
        return Paragraph(escape(display_text(value)).replace('\n','<br/>'),style)
    title_paragraph=paragraph(title,title_style)
    params=paragraph('\n'.join(subtitles),parameter_style)
    _,title_height=title_paragraph.wrap(available-70,page_height)
    _,parameter_height=params.wrap(available-70,page_height)
    header_height=max(52,title_height+parameter_height+10)
    if header_height>page_height-150:
        raise PDFExportError('The report parameters are too long for Letter paper. Use CSV or XLSX.')
    body_top=page_height-24-header_height-12
    footer_text='Generated: '+timestamp

    class NumberedCanvas(Canvas):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            self.page_states=[]
        def showPage(self):
            self.page_states.append(dict(self.__dict__))
            self._startPage()
        def save(self):
            states=list(self.page_states)
            for state in states:
                self.__dict__.update(state)
                self.saveState()
                self.setFont('Helvetica',7)
                self.drawString(24,17,footer_text)
                self.drawRightString(page_width-24,17,f'Page {self._pageNumber} of {len(states)}')
                self.restoreState()
                super().showPage()
            super().save()

    def header(canvas,doc):
        canvas.saveState()
        logo=Path(__file__).resolve().parents[1]/'assets'/'efns_logo.png'
        canvas.drawImage(str(logo),24,page_height-74,width=52,height=50,preserveAspectRatio=True,mask='auto')
        title_paragraph.drawOn(canvas,94,page_height-24-title_height)
        params.drawOn(canvas,94,page_height-29-title_height-parameter_height)
        canvas.setStrokeColor(colors.lightgrey)
        canvas.line(24,body_top+6,page_width-24,body_top+6)
        canvas.restoreState()

    buffer=BytesIO()
    # Remove the frame's default inner 6pt padding so column widths use all of
    # the measured body width, without any right-edge overflow.
    from reportlab.platypus import Frame, PageTemplate, BaseDocTemplate
    doc=BaseDocTemplate(buffer,pagesize=pagesize,leftMargin=24,rightMargin=24,
        topMargin=page_height-body_top,bottomMargin=32,title=title,author='Egg Farmers of Nova Scotia')
    doc.addPageTemplates(PageTemplate(id='report',frames=[Frame(24,32,available,body_top-32,
        leftPadding=0,rightPadding=0,topPadding=0,bottomPadding=0)],onPage=header))
    story=[]
    if rows:
        size,widths=layout
        normal=ParagraphStyle('cell',fontName='Helvetica',fontSize=size,leading=size+2,splitLongWords=True)
        right=ParagraphStyle('number',parent=normal,alignment=TA_RIGHT)
        bold=ParagraphStyle('total',parent=normal,fontName='Helvetica-Bold')
        bold_right=ParagraphStyle('total-number',parent=bold,alignment=TA_RIGHT)
        over_quota=ParagraphStyle('over-quota-total',parent=bold_right,textColor=colors.HexColor('#c00000'))
        marked=set(frame.attrs.get('over_quota_total_rows', [])) if report_id=='producers-over-quota' else set()
        atomic=ParagraphStyle('identifier',parent=normal,splitLongWords=False)
        bold_atomic=ParagraphStyle('total-identifier',parent=bold,splitLongWords=False)
        cell_rows=[]
        styles=[('BACKGROUND',(0,0),(-1,0),colors.Color(*FORM_BLUE)),
            ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#999999')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]
        for index,row in enumerate(rows):
            total=index>0 and is_total_row(rows[0],row)
            if total:styles.append(('BACKGROUND',(0,index),(-1,index),colors.HexColor('#dddddd')))
            cell_rows.append([paragraph(value,over_quota if total and index-1 in marked and rows[0][col]=='% Quota' else bold if index==0 else
                bold_atomic if total and keep_identifiers and identifier_cell(rows[0][col],value) else
                atomic if keep_identifiers and identifier_cell(rows[0][col],value) else
                bold_right if total and NUMERIC.fullmatch(value) else bold if total else
                right if NUMERIC.fullmatch(value) else normal) for col,value in enumerate(row)])
        table=LongTable(cell_rows,colWidths=widths,repeatRows=1,splitByRow=1,splitInRow=1,hAlign='LEFT')
        table.setStyle(TableStyle(styles))
        story.append(table)
    if frame.empty:
        story.extend([Spacer(1,10),paragraph('No records found',parameter_style)])
    footnotes=note_lines(frame,notes)
    if footnotes:
        story.extend([Spacer(1,12),paragraph('Notes',title_style),Spacer(1,5)])
        for note in footnotes:story.extend([paragraph(note,parameter_style),Spacer(1,4)])
    doc.build(story,canvasmaker=NumberedCanvas)
    return buffer.getvalue()
