"""Presentation-only, CSV-value-preserving SSRS-style report PDFs."""
import csv
from datetime import datetime, timezone
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


def table_layout(rows, available_width):
    """Fit every column, wrapping text and preserving a minimum 7pt font."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    columns=len(rows[0])
    # A bounded sample avoids measuring millions of strings; all actual cells
    # still wrap inside their assigned widths when the table is rendered.
    sample=rows[:101]+rows[-1:]
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
            required=max(size+4,widest_char+5,numeric_width)
            essential.append(required)
            word_width=max((stringWidth(word,'Helvetica-Bold',size) for text in texts for word in text.split()),default=0)+5
            minimum.append(max(required,min(28,word_width)))
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


def render_report_pdf(title, subtitle_lines, frame, notes=None, *, generated_at=None):
    """Return PDF bytes for the exact export frame. No repository access."""
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
    pagesize=landscape(letter) if len(frame.columns)>7 else letter
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
    rows=csv_display_rows(frame)
    story=[]
    if rows:
        size,widths=table_layout(rows,available)
        normal=ParagraphStyle('cell',fontName='Helvetica',fontSize=size,leading=size+2,splitLongWords=True)
        right=ParagraphStyle('number',parent=normal,alignment=TA_RIGHT)
        bold=ParagraphStyle('total',parent=normal,fontName='Helvetica-Bold')
        bold_right=ParagraphStyle('total-number',parent=bold,alignment=TA_RIGHT)
        cell_rows=[]
        styles=[('BACKGROUND',(0,0),(-1,0),colors.Color(*FORM_BLUE)),
            ('GRID',(0,0),(-1,-1),.35,colors.HexColor('#999999')),('VALIGN',(0,0),(-1,-1),'TOP'),
            ('LEFTPADDING',(0,0),(-1,-1),2),('RIGHTPADDING',(0,0),(-1,-1),2),
            ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3)]
        for index,row in enumerate(rows):
            total=index>0 and is_total_row(rows[0],row)
            if total:styles.append(('BACKGROUND',(0,index),(-1,index),colors.HexColor('#dddddd')))
            cell_rows.append([paragraph(value,bold if index==0 else
                bold_right if total and NUMERIC.fullmatch(value) else bold if total else
                right if NUMERIC.fullmatch(value) else normal) for value in row])
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
