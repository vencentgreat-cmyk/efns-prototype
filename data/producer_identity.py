"""Exact producer resolution and non-merging source identities. No fuzzy matching."""
import hashlib
import pandas as pd

def text(value):
    if value is None or pd.isna(value):return None
    value=str(value).strip()
    return None if value.casefold() in {'','none','null','nan','nat'} else value

def resolve_producer(record,accounts):
    source=text(record.get('PRODUCER_NUMBER')); supplied=text(record.get('PRODUCER_ACCOUNT_ID'))
    if supplied:
        found=accounts[accounts.ACCOUNT_ID.astype(str).str.casefold()==supplied.casefold()]
        return {'status':'UNIQUE_MATCHED' if len(found)==1 else 'NO_CANDIDATE','account_id':str(found.iloc[0].ACCOUNT_ID) if len(found)==1 else None,'method':'SOURCE_GUID','basis':'Exact supplied Account GUID; existence checked; canonical stored Account ID retained','source_number':source}
    if not source:return {'status':'MISSING_SOURCE_ID','account_id':None,'method':'NONE','basis':'Source provides neither Account GUID nor Producer #','source_number':None}
    ids=accounts.ACCOUNT_ID.astype(str).str.casefold()==source.casefold()
    numbers=accounts.get('REGISTRATION_NUMBER',pd.Series(None,index=accounts.index,dtype=object)).map(text).map(lambda v:v is not None and v.casefold()==source.casefold())
    found=accounts[ids|numbers].drop_duplicates('ACCOUNT_ID')
    return {'status':'UNIQUE_MATCHED' if len(found)==1 else 'MULTIPLE_CANDIDATES' if len(found)>1 else 'NO_CANDIDATE',
            'account_id':str(found.iloc[0].ACCOUNT_ID) if len(found)==1 else None,
            'method':'EXACT_ACCOUNT_ID' if ids.any() else 'EXACT_REGISTRATION_NUMBER',
            'basis':'Exact source Producer # compared with Account GUID/registration; no name matching', 'source_number':source}

def production_identities(frame):
    result=frame.copy()
    def identity(row):
        account=text(row.get('PRODUCER_ACCOUNT_ID')); number=text(row.get('PRODUCER_NUMBER'))
        if account:return pd.Series(['ACCOUNT:'+account.casefold(),text(row.get('PRODUCER_ACCOUNT_NAME')) or account,'ACCOUNT_LINKED'])
        scope=text(row.get('SOURCE_FILE_ID')) or text(row.get('IMPORT_ID')) or 'unscoped'
        if number:
            key=hashlib.sha256((scope+'\0'+number.casefold()).encode()).hexdigest()
            return pd.Series(['SOURCE:'+key,'Source Producer # '+number+' ['+scope[:12]+']',text(row.get('MATCH_STATUS')) or 'UNMATCHED_SOURCE_NUMBER'])
        key=text(row.get('PRODUCTION_ID'))
        if not key:raise ValueError('A production row without producer identity must have its own Production ID.')
        return pd.Series(['UNIDENTIFIED:'+key,'Identity missing; record '+key,'MISSING_SOURCE_ID'])
    if result.empty:
        for f in ('PRODUCER_IDENTITY_KEY','PRODUCER_IDENTITY_LABEL','PRODUCER_IDENTITY_STATUS'):result[f]=pd.Series(dtype=str)
    else:result[['PRODUCER_IDENTITY_KEY','PRODUCER_IDENTITY_LABEL','PRODUCER_IDENTITY_STATUS']]=result.apply(identity,axis=1)
    return result
