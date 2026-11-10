"""Production Data load boundary, safe fallback and exact CSV contracts."""
from decimal import Decimal
from io import StringIO

import pandas as pd
import pytest
import streamlit as st

from tests.test_sara_feedback import entry_app, production_sources
from tests.test_staff_workflows import chain


def production_repo(chain):
    repo,*_=chain
    records,details,accounts=production_sources()
    repo._production=records.merge(details,on='PRODUCTION_ID',how='left')
    repo._accounts=accounts
    return repo


def test_no_year_never_reads_full_range_details(chain,tmp_path,monkeypatch):
    repo=production_repo(chain)
    reads=[];original=repo.get_production_report_records
    def read(start,end):
        reads.append((start,end));return original(start,end)
    monkeypatch.setattr(repo,'get_production_report_records',read)
    app=entry_app(repo,tmp_path,monkeypatch,'2_Production_Data',view='list')
    assert not app.exception and not reads
    assert len(app.dataframe[0].value)==2
    assert any('Select a Reporting Year to load detail columns' in c.value for c in app.caption)
    app.selectbox(key='production_week_filter').select(2).run()
    assert not app.exception and not reads  # Week alone is not a bounded-year read.
    app.selectbox(key='production_year_filter').select(2026).run()
    assert not app.exception and reads==[(202602,202602)]
    assert not any('Select a Reporting Year to load detail columns' in c.value for c in app.caption)


@pytest.mark.parametrize('failure',['missing','duplicate'])
def test_bad_detail_identity_warns_and_keeps_original_rows(chain,tmp_path,monkeypatch,failure):
    repo=production_repo(chain)
    _,details,_=production_sources()
    if failure=='missing':details.loc[0,'PRODUCTION_ID']=None
    else:details=pd.concat([details,details],ignore_index=True)
    monkeypatch.setattr(repo,'get_production_report_records',lambda *args:details)
    app=entry_app(repo,tmp_path,monkeypatch,'2_Production_Data',view='list')
    app.selectbox(key='production_year_filter').select(2026).run()
    assert not app.exception
    assert any('Production details are unavailable; showing original records.' in w.value for w in app.warning)
    frame=app.dataframe[0].value
    assert frame.PRODUCTION_ID.tolist()==['p1','p2']
    assert Decimal(str(frame.iloc[0].TOTAL))==Decimal('24945.0000')
    assert not any('Production detail records have' in w.value for w in app.warning)


@pytest.mark.parametrize('year',[None,2026])
def test_actual_page_csv_row_count_and_unrounded_source_values(chain,tmp_path,monkeypatch,year):
    repo=production_repo(chain)
    exports={};download=st.download_button
    def capture(label,data,*args,**kwargs):
        exports[label]=data
        return download(label,data,*args,**kwargs)
    monkeypatch.setattr(st,'download_button',capture)
    app=entry_app(repo,tmp_path,monkeypatch,'2_Production_Data',view='list')
    if year:app.selectbox(key='production_year_filter').select(year).run()
    assert not app.exception
    table=app.dataframe[0].value
    csv=pd.read_csv(StringIO(exports['Export filtered CSV']),dtype=str,keep_default_na=False)
    assert len(csv)==len(table)==2
    assert list(csv)==list(table) and csv.PRODUCTION_ID.tolist()==table.PRODUCTION_ID.tolist()
    assert csv.iloc[0].J=='0.1250' and csv.iloc[0].TOTAL=='24945.0000'
    assert Decimal(csv.iloc[0].J)==Decimal(str(table.iloc[0].J))
    assert Decimal(csv.iloc[0].TOTAL)==Decimal(str(table.iloc[0].TOTAL))
    assert Decimal(csv.iloc[0].TOTAL)!=sum(Decimal(csv.iloc[0][c]) for c in ['J','XL','L','M','S','PW','B','C'])
    assert csv.iloc[1].J==csv.iloc[1].TOTAL==''
