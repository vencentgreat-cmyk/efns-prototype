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
    return [f'{key}: {value}' for key,value in configuration.items()
            if value is not None and value != [] and value != {} and value != ()]
