"""Permission-checked PDF downloads; use existing REPORT export audit events."""
from app.security import Permission, has_permission, require_permission
from app.services.report_pdf import render_report_pdf, PDFExportError, ensure_pdf_row_limit


def audit_pdf_export(user,report_id,row_count):
    from app.auth import get_auth_store
    require_permission(user,Permission.EXPORT_REPORT)
    get_auth_store().record_action(user,'EXPORT','REPORT',report_id,{'format':'PDF','row_count':row_count})


def pdf_download_button(user,frame,title,subtitle_lines,filename,report_id,*,notes=None,key=None,target=None):
    if not has_permission(user,Permission.EXPORT_REPORT):
        return
    import streamlit as st
    target=target if target is not None else st
    try:
        ensure_pdf_row_limit(len(frame))
        pdf=render_report_pdf(title,subtitle_lines,frame,notes,report_id=report_id)
    except PDFExportError as exc:
        target.info(str(exc))
        target.button('Export PDF',disabled=True,key=key)
        return
    if target.download_button('Export PDF',pdf,filename,'application/pdf',key=key,width='stretch'):
        audit_pdf_export(user,report_id,len(frame))


def custom_parameter_lines(configuration):
    """Describe the saved/run configuration, never the current unsaved widgets."""
    from app.services.report_center import CUSTOM_DATASETS, FLOCK_RECORD_COUNT, FLOCK_RECORD_COUNT_LABEL
    from app.services.report_pdf import display_text

    dataset = configuration.get('dataset')
    if dataset not in CUSTOM_DATASETS:
        return []
    fields = {field.source: field.label for field in CUSTOM_DATASETS[dataset][2]}
    fields[FLOCK_RECORD_COUNT] = FLOCK_RECORD_COUNT_LABEL

    def value_text(value):
        if isinstance(value, (list, tuple)):
            return ', '.join(filter(None, (value_text(item) for item in value)))
        if isinstance(value, (dict, bool)):
            return ''
        text = display_text(value)
        return '' if text == 'All' else text

    account_label = ('Producer Account' if dataset == 'Production Records' else
        'Flock Account' if dataset in {'Flocks', 'Flock Transactions'} else
        'Owner or Related Account' if dataset == 'Quota Transactions' else 'Account')
    labels = {source.lower(): label for source, label in fields.items()}
    labels.update({'account_id': account_label, 'facility_id': 'Facility', 'flock_id': 'Flock',
        'farm_location_id': 'Farm Location', 'facility_account_id': 'Facility Account',
        'flock_account_id': 'Flock Account', 'statuses': 'Status', 'quota_type': 'Quota Type',
        'transaction_type': 'Transaction Type', 'source_scope': 'Source scope',
        'keyword': 'Search', 'facility_detail_id': 'Facility Detail',
        'quota_id': 'Quota Registration', 'grader_number': 'Grader Number', 'barn_identity': 'Barn'})
    lines = [f'Dataset: {dataset}']
    filters = configuration.get('filters') or {}
    for key, value in filters.items():
        label = labels.get(key.lower())
        text = value_text(value)
        if label and text and key not in {'date_from', 'date_to', 'date_field'}:
            lines.append(f'{label}: {text}')
    start, end = (value_text(filters.get(key)) for key in ('date_from', 'date_to'))
    if start or end:
        date_field = filters.get('date_field')
        if not date_field:
            date_field = next((field.source for field in CUSTOM_DATASETS[dataset][2]
                               if field.data_type == 'date'), None)
        label = fields.get(date_field, 'Date range')
        period = f'{start} to {end}' if start and end else f'from {start}' if start else f'through {end}'
        lines.append(f'{label}: {period}')
    sort = fields.get(configuration.get('sort_by'))
    if sort:
        direction = 'ascending' if configuration.get('ascending', True) else 'descending'
        lines.append(f'Sorted by: {sort} ({direction})')
    groups = configuration.get('group_by') or []
    if isinstance(groups, str):
        groups = [groups]
    groups = [fields[field] for field in groups if field in fields]
    if groups:
        lines.append('Grouped by: ' + ', '.join(groups))
    return lines
