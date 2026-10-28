"""Provisional account Bird Count: no invented quota baseline or deltas."""
from decimal import Decimal, InvalidOperation
import pandas as pd
from data.producer_identity import text


def usage_numbers(known_total, missing, baseline=None, *, compatible_units=False):
    result=dict(applicable_quota=baseline,current_occupancy=known_total if not missing else None,
        remaining_capacity=None,usage_percent=None)
    if missing or known_total is None or baseline is None or not compatible_units:
        return result
    base=Decimal(str(baseline))
    if not base.is_finite() or base < 0: return result
    result['remaining_capacity']=base-Decimal(str(known_total))
    if base != 0: result['usage_percent']=Decimal(str(known_total))/base*100
    return result


def account_usage_context(repo, account_id):
    if not text(account_id):
        return dict(account_id=None,summaries=[],facility_details=pd.DataFrame(),reasons=['Missing Account identity; no global records were loaded.'],quotas=pd.DataFrame(),transaction_count=0,scope='Account-wide')
    flocks=repo.get_flocks(account_id=account_id).copy()
    quotas=repo.get_quota_registrations(account_id=account_id).copy()
    facilities=repo.get_facilities(account_id=account_id)
    activity=repo.get_quota_transactions(account_id=account_id)
    if not activity.empty: activity=activity[activity.OWNER_ACCOUNT_ID==account_id]
    reasons=[]
    conflicting=set()
    if not flocks.empty:
        # Dedupe FLOCK_ID before grouping; never multiply by a Facility join.
        fields=['FLOCK_ID','ACCOUNT_ID','FACILITY_ID','FLOCK_QUOTA_TYPE','BIRD_COUNT']
        duplicate=flocks[flocks.FLOCK_ID.duplicated(keep=False)]
        if not duplicate.empty:
            counts=duplicate[fields].drop_duplicates().groupby('FLOCK_ID').size()
            conflicting=set(counts[counts>1].index)
            if conflicting: reasons.append('Conflicting duplicate Flock IDs are excluded from known quantities and shown as ambiguous; totals are incomplete.')
        flocks=flocks.drop_duplicates('FLOCK_ID')
    labels={}
    if not facilities.empty:
        for fid,group in facilities.groupby('FACILITY_ID'):
            labels[fid]=group.FACILITY_NAME.iloc[0] if group.FACILITY_NAME.nunique()==1 else 'Ambiguous Facility label'
    rows=[]
    for f in flocks.to_dict('records'):
        if f['FLOCK_ID'] in conflicting:
            f=dict(f,BIRD_COUNT=None,FACILITY_ID=None,FLOCK_QUOTA_TYPE='Ambiguous type')
        try:
            number=Decimal(str(f.get('BIRD_COUNT')))
            if not number.is_finite() or number < 0: raise InvalidOperation
        except (InvalidOperation,ValueError,TypeError): number=None
        fid=text(f.get('FACILITY_ID'))
        rows.append(dict(flock_id=f['FLOCK_ID'],quota_type=text(f.get('FLOCK_QUOTA_TYPE')) or 'Unknown type',
            facility_id=fid or 'No Facility',facility=labels.get(fid,fid) if fid else 'No Facility',
            value=number,status=text(f.get('STATUS')) or 'Unknown'))
    types=set(text(q.get('QUOTA_TYPE')) or 'Unknown type' for q in quotas.to_dict('records')) | {r['quota_type'] for r in rows}
    summaries=[];details=[]
    for kind in sorted(types):
        selected=[r for r in rows if r['quota_type']==kind]
        known=[r['value'] for r in selected if r['value'] is not None]
        missing=len(selected)-len(known)
        total=sum(known,Decimal(0)) if known else (Decimal(0) if not selected else None)
        summaries.append(dict(quota_type=kind,flock_count=len(selected),known_count=len(known),missing_count=missing,
            known_bird_count=total,registration_count=sum(text(q.get('QUOTA_TYPE'))==kind for q in quotas.to_dict('records')),
            status_counts=pd.Series([r['status'] for r in selected],dtype=object).value_counts().to_dict(),
            **usage_numbers(total,missing,baseline=None)))
        for fid in sorted({r['facility_id'] for r in selected}):
            group=[r for r in selected if r['facility_id']==fid]; values=[r['value'] for r in group if r['value'] is not None]
            details.append({'Quota type':kind,'Facility ID':fid,'Facility':group[0]['facility'],'Flock records':len(group),
                'Known Bird Count':sum(values,Decimal(0)) if values else None,'Missing Bird Count':len(group)-len(values)})
    return dict(account_id=account_id,summaries=summaries,facility_details=pd.DataFrame(details),reasons=reasons,
        quotas=quotas,transaction_count=len(activity),scope='Account-wide, including other Flocks; not a per-Flock or per-Facility allocation')


def quota_usage_context(repo, flock):
    context=account_usage_context(repo,flock.get('ACCOUNT_ID'))
    kind=text(flock.get('FLOCK_QUOTA_TYPE')) or 'Unknown type'
    current=next((r for r in context['summaries'] if r['quota_type']==kind),usage_numbers(None,1))
    return dict(context,**{k:current.get(k) for k in ('applicable_quota','current_occupancy','remaining_capacity','usage_percent')},
        selected_type=kind,linked_flocks=current.get('flock_count',0),recorded_bird_count=flock.get('BIRD_COUNT'))


def render_account_usage(repo, account_id, *, quota_type=None):
    import streamlit as st
    context=account_usage_context(repo,account_id)
    st.subheader('Account quota and Bird Count — provisional')
    st.caption('Account-wide, including other Flocks. Temporarily treats Bird Count as current quantity; registration quota would be a capacity baseline. Business definition remains to be confirmed. All recorded statuses are included; no lifecycle or unit equivalence is inferred.')
    selected=[r for r in context['summaries'] if quota_type is None or r['quota_type']==quota_type]
    if not selected: st.info('No Flock or Quota Registration found for this Account/type.')
    for row in selected:
        with st.container(border=True):
            st.write('Quota type:',row['quota_type'])
            columns=st.columns(4)
            columns[0].metric('Quota baseline','Missing quota baseline')
            columns[1].metric('Known Bird Count',str(row['known_bird_count']) if row['known_bird_count'] is not None else 'Unknown')
            columns[2].metric('Remaining capacity','Cannot calculate')
            columns[3].metric('Account usage','Cannot calculate')
            st.caption(f"{row['flock_count']} unique Flocks; {row['known_count']} known / {row['missing_count']} missing or invalid Bird Count. Incomplete totals are not complete occupancy. {row['registration_count']} registration record(s). Status breakdown: {row['status_counts']}")
    st.info('No quantity/unit field exists on the current Quota Registration. Registration dates/status are not capacity. Quota transaction direction, lease rules and units are not confirmed, so transactions are not added into a balance. Zero baselines would not divide; genuine over-capacity percentages would remain above 100%.')
    for reason in context['reasons']: st.warning(reason)
    details=context['facility_details']
    if quota_type is not None and not details.empty: details=details[details['Quota type']==quota_type]
    st.dataframe(details,hide_index=True,width='stretch')
    st.caption(f"{context['transaction_count']} Account-owner quota transaction record(s), activity only. Reload/Refresh reads current records again. No cached balance, historical transaction replay or estimate-based flock ending.")
    return context


def render_quota_usage(repo, flock):
    return render_account_usage(repo,flock.get('ACCOUNT_ID'),quota_type=text(flock.get('FLOCK_QUOTA_TYPE')) or 'Unknown type')
