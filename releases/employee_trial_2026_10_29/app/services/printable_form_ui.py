"""Streamlit controls and preview for read-only legacy printable PDFs."""
import streamlit as st

from app.security import Permission, has_permission
from app.services.printable_forms import (build_printable_form, matching_pullet_permits,
    render_form_pdf, clean)
from app.services import printable_form_text as wording
from data.business_time import halifax_today
from data.constants import QUOTA_TYPES


def render_printable_form(repo, user, handler):
    accounts = repo.get_accounts()
    rows = accounts.to_dict('records')
    registrations = sorted({clean(r.get('REGISTRATION_NUMBER')) for r in rows if clean(r.get('REGISTRATION_NUMBER'))})
    key = 'print_'+handler
    parameters = {}
    if handler != 'flock_permit_pdf':
        if not registrations:
            st.info('No Accounts with a registration number are available for this form.')
            return
        labels = {value: ' / '.join(clean(r.get('ORGANIZATION_NAME')) for r in rows if clean(r.get('REGISTRATION_NUMBER'))==value) for value in registrations}
        parameters['registration'] = st.selectbox('Registration (layer) number' if handler=='license_application_pdf' else 'Registration number', registrations,
            format_func=lambda value: value+' · '+labels[value],key=key+'_registration')
    if handler == 'license_application_pdf':
        parameters['license_category'] = st.selectbox('Producer/Specialty License',['Producer','Specialty'],key=key+'_category')
        parameters['license_type'] = st.text_input('License Type',value='Renewal',key=key+'_license_type')
        parameters['quota_type'] = st.selectbox('Quota Type',list(QUOTA_TYPES),index=list(QUOTA_TYPES).index('Egg Production'),key=key+'_quota_type')
        parameters['report_date'] = st.date_input('Flock Status Report Date',value=halifax_today(),key=key+'_date')
    elif handler == 'flock_permit_pdf':
        flocks = repo.get_flocks()
        permits = sorted({clean(r.get('PERMIT_NUMBER')) for r in flocks.to_dict('records') if clean(r.get('PERMIT_NUMBER')).startswith('4')})
        if not permits:
            st.info('No Layer permits are available for this form.')
            return
        parameters['layer_permit'] = st.selectbox('Layer permit number',permits,key=key+'_layer')
        options = matching_pullet_permits(flocks,parameters['layer_permit'])
        chosen = st.selectbox('Pullet permit number',['All matching pullet permits',*options],key=key+'_pullets_'+parameters['layer_permit'])
        parameters['pullet_permits'] = options if chosen=='All matching pullet permits' else [chosen]
        if not options:st.info('This Layer permit has no matching Pullet permit; sections B and C will be blank.')
    else:
        tests = repo.get_salmonella_tests()
        owners = {clean(r.get('ACCOUNT_ID')) for r in rows if clean(r.get('REGISTRATION_NUMBER'))==parameters['registration']}
        permits = sorted({clean(r.get('PERMIT_NUMBER')) for r in tests.to_dict('records')
                          if clean(r.get('ACCOUNT_ID')) in owners and clean(r.get('PERMIT_NUMBER'))})
        parameters['layer_permit'] = st.selectbox('Permit number',['All',*permits],key=key+'_permit')
        if parameters['layer_permit']=='All':parameters['layer_permit']=None
        result_labels = {'All':'All','Pass':'SE Not Present','Fail':'SE Present'}
        parameters['result_filter'] = st.selectbox('Pass/Fail',list(result_labels),format_func=result_labels.get,key=key+'_result')
        use_dates = st.checkbox('Filter sample dates',value=False,key=key+'_use_dates')
        dates = st.columns(2)
        start = dates[0].date_input('Sample date start',value=halifax_today().replace(day=1),disabled=not use_dates,key=key+'_start')
        end = dates[1].date_input('Sample date end',value=halifax_today(),disabled=not use_dates,key=key+'_end')
        if use_dates:parameters.update(sample_start=start,sample_end=end)
    # Rebuild only on request; show no stale document after any parameter change.
    fingerprint = repr(parameters)
    if st.session_state.get(key+'_parameters') != fingerprint:
        st.session_state.pop(key+'_document',None)
    if st.button('Generate PDF',key='run_'+handler,type='primary'):
        st.session_state.pop(key+'_document',None)
        try:
            form = build_printable_form(repo,handler,user=user,**parameters)
            st.session_state[key+'_document'] = form
            st.session_state[key+'_parameters'] = fingerprint
        except Exception as exc:
            st.info('The form could not be generated: '+str(exc))
    form = st.session_state.get(key+'_document')
    if form is None:return
    if not form.has_data:
        st.info(wording.NO_DATA)
        return
    st.caption('Preview of the selected source data. Missing values are left blank in the PDF.')
    st.dataframe(form.preview,hide_index=True,width='stretch')
    for name,rows in form.tables.items():
        if rows:
            headers = {'barns':wording.BARN_HEADERS,'layers':wording.PERMIT_HEADERS,
                       'pullets':wording.PERMIT_HEADERS,'hatcheries':wording.HATCHERY_HEADERS,'results':wording.RESULT_HEADERS}[name]
            import pandas as pd
            st.dataframe(pd.DataFrame(rows,columns=headers).head(10),hide_index=True,width='stretch')
    if form.missing_fields:st.info('Blank fields: '+ '; '.join(form.missing_fields)+'.')
    for note in form.notes:st.caption(note)
    if has_permission(user,Permission.EXPORT_REPORT):
        try:
            pdf = render_form_pdf(form)
        except Exception as exc:
            st.info('The PDF could not be generated: '+str(exc))
        else:
            st.download_button('Download PDF',pdf,handler+'.pdf','application/pdf',key=key+'_download')
    else:st.info('Your role can preview this form but cannot export it.')
