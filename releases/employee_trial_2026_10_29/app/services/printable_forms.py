"""Read-only form projections and PDF rendering. Existing report rules are untouched."""
from dataclasses import dataclass, field
from datetime import date
from io import BytesIO
from pathlib import Path
import re
from xml.sax.saxutils import escape

import pandas as pd

from app.services import printable_form_text as wording
from data.confirmed_quota_position import confirmed_quota_position
from data.position_evidence import day, number
from data.producer_identity import text

FORM_HANDLERS = ('license_application_pdf', 'flock_permit_pdf', 'salmonella_form_pdf')


def clean(value):
    return text(value) or ''


def records(frame):
    return frame.to_dict('records') if isinstance(frame, pd.DataFrame) else []


def by_id(frame, key):
    return {clean(row.get(key)).casefold(): row for row in records(frame) if clean(row.get(key))}


def short_date(value):
    value = day(value)
    return f'{value.month}/{value.day}/{value.year}' if value else ''


def long_date(value):
    value = day(value)
    return value.strftime('%A, %B ') + str(value.day) + value.strftime(', %Y') if value else ''


def count_text(value):
    value = number(value)
    return format(value, ',f').rstrip('0').rstrip('.') if value is not None and value % 1 else (f'{value:,.0f}' if value is not None else '')


def address(row, *, location=False):
    fields = ('ADDRESS_1', 'ADDRESS_2') if location else ('ADDRESS_LINE1', 'ADDRESS_LINE2', 'ADDRESS_LINE3')
    lines = [clean(row.get(key)) for key in fields if clean(row.get(key))]
    if location:
        return '\n'.join([*lines, *[clean(row.get(key)) for key in ('CITY','PROVINCE','POSTAL_CODE') if clean(row.get(key))]])
    place = ', '.join(filter(None, (clean(row.get('CITY')), clean(row.get('PROVINCE')))))
    place = ' '.join(filter(None, (place, clean(row.get('POSTAL_CODE')))))
    return '\n'.join([*lines, *([place] if place else [])])


@dataclass
class PrintableForm:
    handler: str
    fields: dict = field(default_factory=dict)
    tables: dict = field(default_factory=dict)
    notes: list = field(default_factory=list)
    missing_fields: list = field(default_factory=list)
    has_data: bool = False

    def missing(self, label, value):
        if not clean(value) and label not in self.missing_fields:
            self.missing_fields.append(label)
        return clean(value)

    @property
    def preview(self):
        if not self.has_data:
            return pd.DataFrame(columns=['Field', 'Value'])
        return pd.DataFrame([{'Field': label, 'Value': clean(value)} for label, value in self.fields.items()])


def selected_account(accounts, registration):
    matches = [r for r in records(accounts) if clean(registration) and clean(r.get('REGISTRATION_NUMBER')) == clean(registration)]
    if len(matches) > 1:
        raise ValueError('More than one Account has this registration number; select a unique registration.')
    return matches[0] if matches else None


def facility_context(facility_id, facilities, locations):
    facility = by_id(facilities, 'FACILITY_ID').get(clean(facility_id).casefold(), {})
    location = by_id(locations, 'FARM_LOCATION_ID').get(clean(facility.get('FARM_LOCATION_ID')).casefold(), {})
    return facility, location


def build_license_application(accounts, facilities, locations, registrations, transactions,
                              registration, report_date, inactive_ids, rules,
                              license_category='Producer', license_type='Renewal', quota_type='Egg Production'):
    result = PrintableForm('license_application_pdf')
    account = selected_account(accounts, registration)
    if account is None:
        return result
    if day(report_date) is None:
        raise ValueError('Flock Status Report Date is required.')
    result.has_data = True
    names = by_id(accounts, 'ACCOUNT_ID')
    position = confirmed_quota_position(registrations, transactions, account['ACCOUNT_ID'],
                                        quota_type, report_date, inactive_ids, rules)
    def linked(column):
        stored = clean(account.get(column))
        value = clean(names.get(stored.casefold(), {}).get('ORGANIZATION_NAME'))
        return value or (stored if stored.casefold() == 'self' else '')
    def resolve_self(value):
        return clean(account.get('ORGANIZATION_NAME')) if clean(value).casefold() == 'self' else clean(value)
    result.fields = {
        wording.LICENSE_TYPE: clean(license_category), 'Licence renewal type': clean(license_type),
        wording.ACCOUNT_HEADERS[0]: result.missing('Account Name', account.get('ORGANIZATION_NAME')),
        wording.ACCOUNT_HEADERS[1]: clean(account.get('REGISTRATION_NUMBER')),
        wording.ACCOUNT_HEADERS[2]: result.missing('Mailing Address', address(account)),
        wording.CONTACT_HEADERS[0]: result.missing('Primary Contact', account.get('CONTACT_NAME')),
        wording.CONTACT_HEADERS[1]: result.missing('Phone', account.get('CONTACT_PHONE')),
        wording.CONTACT_HEADERS[2]: result.missing('Email', account.get('CONTACT_EMAIL')),
        wording.QUOTA_AS_OF: long_date(report_date), 'Quota': count_text(position['net_position']),
        wording.RELATIONSHIP_HEADERS[0]: result.missing('Grading Station', resolve_self(linked('GRADING_STATION_ACCOUNT_ID'))),
        wording.RELATIONSHIP_HEADERS[1]: result.missing('Spent Fowl Plan', resolve_self(linked('SPENT_FOWL_PLANS_ACCOUNT_ID') or clean(account.get('SPENT_FOWL_PLANS')))),
        wording.RELATIONSHIP_HEADERS[2]: result.missing('Pullet Grower', resolve_self(linked('PULLET_GROWER_ACCOUNT_ID'))),
    }
    result.notes.extend(position['reasons'])
    if position['net_position'] is None:
        result.missing('Confirmed quota position', '')
    barns = []
    for facility in records(facilities):
        if clean(facility.get('ACCOUNT_ID')).casefold() != clean(account['ACCOUNT_ID']).casefold():
            continue
        if clean(facility.get('STATUS')).casefold() != 'active' or clean(facility.get('FACILITY_TYPE')).casefold() != 'layers':
            continue
        _, location = facility_context(facility.get('FACILITY_ID'), facilities, locations)
        barns.append([result.missing('Barn Name', facility.get('FACILITY_NAME')),
                      result.missing('Housing System (Facility Type column)', facility.get('HOUSING_SYSTEM')),
                      result.missing('Barn Address (linked Farm Location)', address(location, location=True))])
    result.tables['barns'] = sorted(barns, key=lambda row: row[0])
    if not barns:
        result.notes.append('No Active Layers barns are recorded for the selected Account.')
    return result


def build_salmonella_form(accounts, flocks, facilities, tests, registration, permit,
                          result_filter='All', sample_start=None, sample_end=None):
    form = PrintableForm('salmonella_form_pdf')
    owner = selected_account(accounts, registration)
    if owner is None:
        return form
    if sample_start is not None and sample_end is not None and day(sample_start) and day(sample_end) and day(sample_start) > day(sample_end):
        raise ValueError('Sample date start must be on or before sample date end.')
    flock_map = by_id(flocks, 'FLOCK_ID')
    facility_map = by_id(facilities, 'FACILITY_ID')
    rows = []
    for test in records(tests):
        flock = flock_map.get(clean(test.get('FLOCK_ID')).casefold(), {})
        if clean(test.get('ACCOUNT_ID')).casefold() != clean(owner['ACCOUNT_ID']).casefold():
            continue
        permit_number = clean(test.get('PERMIT_NUMBER')) or clean(flock.get('PERMIT_NUMBER'))
        if clean(permit) and permit_number != clean(permit):
            continue
        sampled = day(test.get('TESTING_DATE'))
        if sample_start and (sampled is None or sampled < day(sample_start)):
            continue
        if sample_end and (sampled is None or sampled > day(sample_end)):
            continue
        stored_result = clean(test.get('TEST_RESULT'))
        accepted = {'pass': {'pass','negative'}, 'fail': {'fail','positive'}}.get(clean(result_filter).casefold(), {clean(result_filter).casefold()})
        if result_filter != 'All' and stored_result.casefold() not in accepted:
            continue
        facility = facility_map.get(clean(flock.get('FACILITY_ID')).casefold(), {})
        result_date = test.get('DATE_RESULT_SENT')
        if result_date is None or pd.isna(result_date):
            result_date = test.get('DATE_RECEIVED')
        rows.append([clean(registration), permit_number,
                     form.missing('Facility', facility.get('FACILITY_NAME')), short_date(sampled),
                     form.missing('Date Result', short_date(result_date)),
                     form.missing('Sample Result', stored_result), clean(test.get('COMMENTS'))])
        if sampled is None:
            form.missing('Sample Date', '')
    rows.sort(key=lambda row: (row[1], day(row[3]) or date.min))
    form.has_data = bool(rows)
    form.fields = {'Registration Number': clean(registration), 'Permit No': clean(permit)}
    form.tables['results'] = rows
    return form


def matching_pullet_permits(flocks, layer_permit):
    """Supplied legacy example: layer 40403 pairs with 30403, 30403a, 30403b.

    This is a permit-number relationship only; it never infers Account links.
    """
    match = re.fullmatch(r'4(\d{4})', clean(layer_permit))
    if not match:
        return []
    pattern = re.compile(r'3'+match.group(1)+r'[a-z]*', re.IGNORECASE)
    return sorted({clean(r.get('PERMIT_NUMBER')) for r in records(flocks)
                   if pattern.fullmatch(clean(r.get('PERMIT_NUMBER')))}, key=str.casefold)


def build_flock_permit(accounts, flocks, facilities, locations, layer_permit, pullet_permits=None):
    form = PrintableForm('flock_permit_pdf')
    layers = [r for r in records(flocks) if clean(layer_permit) and clean(r.get('PERMIT_NUMBER')) == clean(layer_permit)]
    if not layers:
        return form
    if len(layers) != 1:
        raise ValueError('More than one flock has the selected Layer permit number.')
    options = matching_pullet_permits(flocks, layer_permit)
    selected = options if pullet_permits is None else [clean(v) for v in pullet_permits]
    if any(value not in options for value in selected):
        raise ValueError('Pullet permits must match the selected Layer permit number.')
    pullets = [r for r in records(flocks) if clean(r.get('PERMIT_NUMBER')) in selected]
    if len(pullets) != len(set(clean(r.get('PERMIT_NUMBER')) for r in pullets)):
        raise ValueError('More than one flock has a selected Pullet permit number.')
    owners = by_id(accounts, 'ACCOUNT_ID')
    def flock_row(flock):
        owner = owners.get(clean(flock.get('ACCOUNT_ID')).casefold(), {})
        facility, location = facility_context(flock.get('FACILITY_ID'), facilities, locations)
        values = (flock.get('PERMIT_NUMBER'), owner.get('REGISTRATION_NUMBER'), owner.get('ORGANIZATION_NAME'),
                  short_date(flock.get('HATCH_DATE')), short_date(flock.get('PLACEMENT_DATE')),
                  count_text(flock.get('BIRD_COUNT')).replace(',',''), flock.get('EGG_COLOUR'), flock.get('BIRD_STRAIN'),
                  facility.get('FACILITY_NAME'), address(location, location=True))
        return [form.missing(label,value) for label,value in zip(wording.PERMIT_HEADERS,values)]
    form.has_data = True
    form.fields = {'Layer permit': clean(layer_permit), 'Pullet permits': ', '.join(selected)}
    form.tables = {'layers': [flock_row(layers[0])],
                   'pullets': [flock_row(r) for r in sorted(pullets,key=lambda r:clean(r.get('PERMIT_NUMBER')))],
                   'hatcheries': []}
    for flock in sorted(pullets,key=lambda r:clean(r.get('PERMIT_NUMBER'))):
        values = (flock.get('PERMIT_NUMBER'), flock.get('HATCHERY'), short_date(flock.get('HATCH_DATE')),
                  count_text(flock.get('BIRD_COUNT')).replace(',',''), flock.get('EGG_COLOUR'), flock.get('BIRD_STRAIN'))
        form.tables['hatcheries'].append([form.missing(label,value) for label,value in zip(wording.HATCHERY_HEADERS,values)])
    if not pullets:
        form.notes.append('No matching Pullet permits were selected or recorded; Pullet Growers and Hatcheries are blank.')
    return form


def build_printable_form(repo, handler, *, user=None, registration=None, report_date=None,
                         license_category='Producer', license_type='Renewal', quota_type='Egg Production',
                         layer_permit=None, pullet_permits=None, result_filter='All', sample_start=None, sample_end=None):
    """Use existing repository reads only. No new SQL or write calls."""
    accounts = repo.get_accounts()
    if handler == 'license_application_pdf':
        from app.services.quota_state import get_inactive_quota_transaction_ids
        from data.quota_position import load_rules
        registrations, transactions = repo.get_quota_registrations(), repo.get_quota_transactions()
        inactive = get_inactive_quota_transaction_ids(repo, transactions.get('QUOTA_TRANSACTION_ID', pd.Series(dtype=object)).tolist(), user=user)
        return build_license_application(accounts, repo.get_facilities(), repo.get_farm_locations(),
            registrations, transactions, registration, report_date, inactive, load_rules(),
            license_category, license_type, quota_type)
    if handler == 'salmonella_form_pdf':
        return build_salmonella_form(accounts, repo.get_flocks(), repo.get_facilities(), repo.get_salmonella_tests(),
                                     registration, None if layer_permit is None else layer_permit,
                                     result_filter, sample_start, sample_end)
    if handler == 'flock_permit_pdf':
        return build_flock_permit(accounts, repo.get_flocks(), repo.get_facilities(), repo.get_farm_locations(), layer_permit, pullet_permits)
    raise ValueError('Unknown printable form.')


def render_form_pdf(form):
    """Render fixed legacy wording, escaped data, repeating table headers and pagination."""
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    if form.handler not in FORM_HANDLERS:
        raise ValueError('Unknown printable form.')
    out = BytesIO()
    permit = form.handler == 'flock_permit_pdf'
    salmonella = form.handler == 'salmonella_form_pdf'
    page_size = landscape(letter) if permit else letter
    width, height = page_size
    margin = 12 if permit else (50 if salmonella else 71)
    top = 120 if permit else (132 if salmonella else 106)
    doc = SimpleDocTemplate(out, pagesize=page_size, leftMargin=margin, rightMargin=margin,
                            topMargin=top, bottomMargin=58, title=wording.PERMIT_TITLE if permit else ' / '.join(wording.SALMONELLA_TITLE if salmonella else wording.LICENSE_TITLE),
                            author=wording.LICENSE_TITLE[0])
    body = ParagraphStyle('body', fontName='Helvetica', fontSize=10, leading=11)
    centered = ParagraphStyle('centered', parent=body, alignment=TA_CENTER)
    fill = colors.Color(*(wording.FORM_BLUE if permit or salmonella else wording.LICENSE_BLUE))
    def p(value, bold=False, center=False):
        content = escape(clean(value)).replace('\n', '<br/>')
        return Paragraph(('<b>'+content+'</b>') if bold else content, centered if center else body)
    def table(headers, rows, widths, *, center=False):
        data = [[p(value, True, center) for value in headers], *[[p(value, center=center) for value in row] for row in rows]]
        result = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
        result.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),fill),
            ('GRID',(0,0),(-1,-1),0.5,colors.black if permit or salmonella else colors.lightgrey),
            ('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),2),
            ('RIGHTPADDING',(0,0),(-1,-1),2),('TOPPADDING',(0,0),(-1,-1),2),('BOTTOMPADDING',(0,0),(-1,-1),3)]))
        return result
    def header(canvas, document):
        canvas.saveState()
        if not permit:
            canvas.setLineWidth(0.5)
            canvas.rect(36, 40 if salmonella else 24, width-72, height-(129 if salmonella else 48))
        else:
            canvas.setLineWidth(.5)
            canvas.rect(0,0,width,height-36)
        logo = Path(__file__).resolve().parents[1]/'assets'/'efns_logo.png'
        if logo.exists():
            # Exact image rectangles measured from the supplied legacy PDFs.
            x,y,w,h = ((17.91,497.841,75.258,71.5) if permit else
                       (53.91,710.75,76.048,72.25) if salmonella else (77.07,698.79,63.47,60.3))
            canvas.drawImage(str(logo),x,y,width=w,height=h,preserveAspectRatio=True,mask='auto')
        if permit:
            canvas.setFont('Helvetica-Bold',18)
            canvas.drawCentredString(376,height-71,clean(form.fields.get('Layer permit')))
            canvas.drawCentredString(376,height-107,wording.PERMIT_TITLE)
            half=canvas.stringWidth(wording.PERMIT_TITLE,'Helvetica-Bold',18)/2
            canvas.line(376-half,height-109,376+half,height-109)
            canvas.setFont('Helvetica',9)
            for i,line in enumerate(wording.EFNS_ADDRESS):canvas.drawString(width-172,height-61-i*11,line)
        else:
            titles = wording.SALMONELLA_TITLE if salmonella else wording.LICENSE_TITLE
            canvas.setFont('Helvetica-Bold',14 if salmonella else 17)
            for i,line in enumerate(titles):
                if salmonella:canvas.setFont('Helvetica-BoldOblique' if i==0 else 'Helvetica-Bold',14)
                x,y=333 if salmonella else 345,height-(106 if salmonella else 53)-i*18
                canvas.drawCentredString(x,y,line)
                if salmonella:
                    half=canvas.stringWidth(line,'Helvetica-BoldOblique' if i==0 else 'Helvetica-Bold',14)/2
                    canvas.line(x-half,y-2,x+half,y-2)
        if salmonella:
            canvas.setFillColor(colors.Color(.392,.584,.929))
            canvas.setFont('Helvetica-Bold',9)
            for i,line in enumerate(wording.SALMONELLA_FOOTER):canvas.drawCentredString(width/2,21-i*11,line)
        canvas.restoreState()
    story = []
    if not form.has_data:
        story.append(p(wording.NO_DATA))
    elif not permit and not salmonella:
        fields = form.fields
        type_table=Table([[p(wording.LICENSE_TYPE,True,True),p(fields.get(wording.LICENSE_TYPE),center=True),p(fields.get('Licence renewal type'),center=True)]],colWidths=[159,102,90],hAlign='LEFT')
        type_table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),fill),('GRID',(0,0),(-1,-1),.5,colors.lightgrey)]))
        story += [type_table, Spacer(1,6)]
        for headers in (wording.ACCOUNT_HEADERS, wording.CONTACT_HEADERS):
            story += [table(headers, [[fields.get(key,'') for key in headers]], [159,102,183], center=True), Spacer(1,6)]
        quota_table = Table([[p(wording.QUOTA_AS_OF+'\n'+fields.get(wording.QUOTA_AS_OF,''),True,True),p(fields.get('Quota',''),center=True)]], colWidths=[162,102],hAlign='LEFT')
        quota_table.setStyle(TableStyle([('BACKGROUND',(0,0),(0,0),fill),('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('VALIGN',(0,0),(-1,-1),'MIDDLE')]))
        story += [quota_table, Spacer(1,6),
                  table(wording.RELATIONSHIP_HEADERS, [[fields.get(key,'') for key in wording.RELATIONSHIP_HEADERS]], [159,135,150], center=True), Spacer(1,6),
                  table(wording.BARN_HEADERS, form.tables.get('barns',[]), [95,120,229], center=True), Spacer(1,16), p(wording.LICENSE_NOTES,True)]
        for declaration in wording.DECLARATIONS:story += [Spacer(1,8),p(declaration)]
        signatures = Table([[p('_____________________________'),p('______________________')],
                            [p(wording.SIGNATURE),p(wording.SIGNATURE_DATE)]], colWidths=[290,168], hAlign='LEFT')
        story += [Spacer(1,28), signatures]
    elif salmonella:
        story += [p(wording.NOTIFICATION), Spacer(1,12), p(wording.MARKET_RESTRICTION,True), Spacer(1,12), p(wording.FARM_GATE), Spacer(1,12),
                  table(wording.RESULT_HEADERS,form.tables.get('results',[]),[65,50,64,56,64,50,151]),Spacer(1,6),p(wording.RESULT_CLOSING)]
    else:
        for section,key in zip(wording.PERMIT_SECTIONS,('layers','pullets','hatcheries')):
            headings = wording.HATCHERY_HEADERS if key=='hatcheries' else wording.PERMIT_HEADERS
            widths = [53,126,64,100,42,47] if key=='hatcheries' else [53,55,73,64,64,36,40,47,73,239]
            title_table = table((section,),[],[sum(widths)])
            story += [title_table,table(headings,form.tables.get(key,[]),widths),Spacer(1,16)]
    doc.build(story,onFirstPage=header,onLaterPages=header)
    return out.getvalue()
