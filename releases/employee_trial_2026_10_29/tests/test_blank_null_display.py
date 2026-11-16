"""Null rendering only: identical Arrow values and exports with/without placeholder."""
from copy import deepcopy
import datetime as dt
from io import BytesIO

import pandas as pd
import pytest
import streamlit as st

from app.services.report_center import report_csv, report_xlsx
from tests.test_flocks_accounts_legacy_labels import legacy_chain, open_page, ENTRIES
from tests.test_staff_workflows import chain
from tests.test_report_center import user


@pytest.mark.parametrize('entry,prefix',ENTRIES)
@pytest.mark.parametrize('page',['flock','account'])
def test_null_placeholder_preserves_table_values_and_exports(legacy_chain,tmp_path,monkeypatch,entry,prefix,page):
    repo,account,_,flock=legacy_chain
    missing=[None,float('nan'),pd.NA,'','Ordinary text','None supplied by producer']
    attr='_flocks' if page=='flock' else '_accounts'
    rows=[]
    original=getattr(repo,attr).iloc[0].to_dict()
    for index,value in enumerate(missing):
        row=dict(original)
        # Match the maintained Snowflake TIMESTAMP_NTZ fields, not mock UTC stamps.
        row.update(CREATED_AT=dt.datetime(2026,1,1),UPDATED_AT=dt.datetime(2026,1,2))
        if page=='flock':
            row.update(FLOCK_ID=flock if index==0 else f'synthetic-flock-{index}',
                COMMENTS=value,DISPOSAL_PLANT=value,HATCHERY=value,BREEDER=value,
                BIRD_COUNT=0 if index==0 else 100+index,
                DISPOSAL_DATE=None if index%2==0 else dt.date(2027,1,1))
        else:
            row.update(ACCOUNT_ID=account if index==0 else f'synthetic-account-{index}',
                REGISTRATION_NUMBER=f'{index+1:03}',CONTACT_NAME=value,CONTACT_EMAIL=value,
                ADDRESS_LINE1=value,CITY=value,BREEDER_ROLE=False)
        rows.append(row)
    setattr(repo,attr,pd.DataFrame(rows,dtype=object))
    before_source={name:deepcopy(getattr(repo,name)) for name in ('_flocks','_accounts')}
    app=open_page(legacy_chain,tmp_path,monkeypatch,entry,prefix,page)
    assert not app.exception and not app.error
    grid=app.dataframe[0]
    assert grid.proto.placeholder=='—'
    shown=grid.value.copy(deep=True);arrow_bytes=grid.proto.data
    fields=('COMMENTS','DISPOSAL_PLANT','HATCHERY','BREEDER') if page=='flock' else ('CONTACT_NAME','CONTACT_EMAIL','ADDRESS_LINE1','CITY')
    for field in fields:
        assert shown[field].iloc[:3].isna().all()
        assert shown[field].iloc[3:].tolist()==missing[3:]
    if page=='flock':
        assert shown.iloc[0].BIRD_COUNT==0
        assert pd.isna(shown.iloc[0].DISPOSAL_DATE)
    else:
        assert not shown.BREEDER_ROLE.any()
    csv=report_csv(user(),shown)
    xlsx=pd.read_excel(BytesIO(report_xlsx(user(),shown)))
    row_ids=list(app.session_state['flock_list_row_ids' if page=='flock' else 'account_list_row_ids'])

    # Reproduce the previous rendering call without changing the page or its data.
    render=st.dataframe
    def previous_render(*args,**kwargs):
        if kwargs.get('key') in {'flock_list_grid','account_list_grid'}:
            kwargs.pop('placeholder',None)
        return render(*args,**kwargs)
    monkeypatch.setattr(st,'dataframe',previous_render)
    app.run()
    assert not app.exception and not app.error
    previous=app.dataframe[0]
    assert previous.proto.placeholder==''
    assert previous.proto.data==arrow_bytes
    pd.testing.assert_frame_equal(previous.value,shown)
    assert report_csv(user(),previous.value)==csv
    pd.testing.assert_frame_equal(pd.read_excel(BytesIO(report_xlsx(user(),previous.value))),xlsx)
    assert list(app.session_state['flock_list_row_ids' if page=='flock' else 'account_list_row_ids'])==row_ids
    for name,frame in before_source.items():pd.testing.assert_frame_equal(frame,getattr(repo,name))
