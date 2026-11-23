"""Synthetic, in-memory EIMS workbooks; no real files or live database access."""
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from copy import deepcopy

import pandas as pd
import pytest
import streamlit as st
from openpyxl import Workbook

from data.constants import EIMS_SOURCE_COLUMNS, EIMS_NUMERIC_COLUMNS, EIMS_COLUMN_MAPPING
from data.importing import read_eims_workbook
from data.production_intake import prepare_workbook
from data.production_replacement import (upload_errors, zero_duplicate_warnings,
    PRODUCTION_QUANTITY_COLUMNS)
from data.repositories.snowflake import SnowflakeRepository, PRODUCTION_DECIMAL_COLUMNS, PRODUCTION_COLUMNS
from data.repositories.base import RepositoryError
from tests.test_production_replacement import repo as empty_repo, existing
from app.services.production_reports import build_production_report, build_nest_run_report, AMOUNTS, NEST_FIELDS, production_grader_options
from app.services.production_presentation import production_report_view
from tests.auth_support import authenticated_app


def zero_row(**changes):
    values={column:0 for column in EIMS_NUMERIC_COLUMNS}
    values.update({'Producer #':'001','Grader':'Synthetic grader','Grader#':'G1','Week':202601,
        'MarketingType':'RE','Housing system':'Conventional','Egg Type':'Regular','Colour':'Brown',
        'BARN_IDENTITY':'synthetic-barn'})
    return dict(values,**changes)


def pattern():
    return [zero_row(Colour='White',J=29,Subtotal=29,Total=29),zero_row(),
            zero_row(Colour='White',J=44,L=30,Subtotal=74,Total=74),zero_row()]


def workbook(rows,version='one'):
    book=Workbook();sheet=book.active;sheet.title='EIMS 3'
    columns=[*EIMS_SOURCE_COLUMNS,'BARN_IDENTITY']
    for col,name in enumerate(columns,1):sheet.cell(10,col,name)
    for ordinal,row in enumerate(rows,50):
        for col,name in enumerate(columns,1):sheet.cell(ordinal,col,row.get(name))
    book.properties.description='Synthetic test version '+version
    stream=BytesIO();book.save(stream)
    return stream.getvalue()


def repository():
    result=empty_repo()
    result._accounts['ORGANIZATION_NAME']=['Synthetic producer A','Synthetic producer B']
    return result


def stage(repo,content):
    archive=repo.archive_source_file('synthetic-zero.xlsx',content,'PRODUCTION_WORKBOOK','synthetic-staff')
    raw=read_eims_workbook(BytesIO(content))
    records,rows,errors,warnings=prepare_workbook(raw,archive['SOURCE_FILE_ID'],repo.get_accounts())
    batch=repo.stage_production_upload(dict(SOURCE_FILE_ID=archive['SOURCE_FILE_ID'],FILE_HASH=archive['FILE_HASH'],
        SOURCE_RECORD_COUNT=len(rows),ERROR_COUNT=len(upload_errors(raw,records,errors))),rows)
    return batch,records,rows,upload_errors(raw,records,errors),warnings


def test_white_brown_pairs_keep_every_raw_and_normalized_row():
    r=repository();content=workbook(pattern())
    batch,records,rows,errors,warnings=stage(r,content)
    assert errors==[] and len(records)==len(rows)==4
    assert records.SOURCE_ROW_NUMBER.tolist()==[50,51,52,53]
    assert records.PRODUCTION_ID.nunique()==records.RAW_ROW_ID.nunique()==4
    assert warnings==['2 identical all-zero rows were kept (Excel rows 51, 53).']
    assert all(row['VALIDATION_STATUS']=='VALID' for row in rows)
    assert r.commit_staged_production(batch,'synthetic-staff')==(batch,4)
    assert len(r.get_raw_rows(batch))==len(r._production)==4
    assert r._production.EGG_COLOUR.tolist()==['White','Brown','White','Brown']
    assert r._production.SOURCE_ROW_NUMBER.tolist()==[50,51,52,53]
    by_id={row['RAW_ROW_ID']:row for row in r.get_raw_rows(batch).to_dict('records')}
    for record in r._production.to_dict('records'):
        assert by_id[record['RAW_ROW_ID']]['SOURCE_ROW_NUMBER']==record['SOURCE_ROW_NUMBER']
        assert by_id[record['RAW_ROW_ID']]['TARGET_ID']==record['PRODUCTION_ID']


def test_three_identical_zero_rows_and_distinct_producers_weeks_are_preserved():
    r=repository();batch,records,_,errors,warnings=stage(r,workbook([zero_row()]*3))
    assert not errors and warnings==['3 identical all-zero rows were kept (Excel rows 50, 51, 52).']
    assert r.commit_staged_production(batch,'synthetic-staff')==(batch,3)
    assert len(r._production)==3 and r._production.PRODUCTION_ID.nunique()==3
    r=repository();rows=[]
    for producer,week in [('001',202601),('001',202602),('002',202601)]:
        rows.extend([zero_row(**{'Producer #':producer,'Week':week})]*2)
    batch,records,_,errors,warnings=stage(r,workbook(rows))
    assert not errors and len(warnings)==1 and '6 identical all-zero rows in 3 groups' in warnings[0]
    assert r.commit_staged_production(batch,'synthetic-staff')==(batch,6)
    single=records.iloc[[0,2,4]].copy()
    assert zero_duplicate_warnings(single)==[]


def test_blank_and_zero_quantity_spellings_are_only_compared_not_rewritten():
    raw=read_eims_workbook(BytesIO(workbook([zero_row(),zero_row(J=None,Total=None)])))
    records,rows,errors,warnings=prepare_workbook(raw,'synthetic-file',repository().get_accounts())
    assert not upload_errors(raw,records,errors)
    assert '2 identical all-zero rows were kept (Excel rows 50, 51).' in warnings
    assert records.iloc[0].JUMBO==0 and records.iloc[1].JUMBO is None
    assert rows[1]['RAW_DATA']['J'] is None or pd.isna(rows[1]['RAW_DATA']['J'])


@pytest.mark.parametrize('column',sorted(PRODUCTION_DECIMAL_COLUMNS))
def test_any_nonzero_production_quantity_keeps_the_exact_blocking_message(column):
    raw=read_eims_workbook(BytesIO(workbook([zero_row(),zero_row()])))
    records,_,errors,_=prepare_workbook(raw,'synthetic-file',repository().get_accounts())
    records[column]=Decimal('0.25')  # Even a value rounding to zero in a report is non-zero input.
    assert upload_errors(raw,records,errors)==['Excel row 51: Identical production row is duplicated inside this workbook.']
    assert zero_duplicate_warnings(records)==[]


def test_quantity_scope_excludes_numeric_identity_and_dimension_fields():
    assert PRODUCTION_QUANTITY_COLUMNS==PRODUCTION_DECIMAL_COLUMNS
    raw=read_eims_workbook(BytesIO(workbook([zero_row(),zero_row()])))
    records,_,errors,_=prepare_workbook(raw,'synthetic-file',repository().get_accounts())
    records['FLOCK_AGE']=21
    before=records.copy(deep=True)
    assert not upload_errors(raw,records,errors)
    assert len(zero_duplicate_warnings(records))==1
    pd.testing.assert_frame_equal(records,before)


def test_duplicate_nonzero_commit_still_blocks_every_row():
    r=repository();row=zero_row(Colour='White',J=29,Subtotal=29,Total=29)
    batch,_,_,errors,warnings=stage(r,workbook([row,row]))
    assert errors==['Excel row 51: Identical production row is duplicated inside this workbook.']
    assert not warnings
    with pytest.raises(RepositoryError,match='Identical production row is duplicated inside this workbook'):
        r.commit_staged_production(batch,'synthetic-staff')
    assert r._production.empty and len(r.get_raw_rows(batch))==2


def test_overwrite_backup_complete_sets_and_exact_file_retry_have_no_collisions():
    r=repository()
    r._production=pd.DataFrame([existing('unrelated-producer','b'),existing('unrelated-week',week=202602)])
    first=workbook(pattern(),'first');batch,records,_,errors,_=stage(r,first)
    assert not errors and r.commit_staged_production(batch,'synthetic-staff')==(batch,4)
    old_ids=set(records.PRODUCTION_ID)
    second=workbook(pattern(),'second');assert first!=second
    newer,prepared,_,errors,_=stage(r,second)
    assert not errors and newer!=batch
    assert r.commit_staged_production(newer,'synthetic-staff')==(newer,4)
    backups=r.get_production_replacement_backups(newer)
    assert len(backups)==4 and set(backups.PRODUCTION_ID)==old_ids
    assert sorted(row['SOURCE_ROW_NUMBER'] for row in backups.OLD_VALUES)==[50,51,52,53]
    assert sum(row['TOTAL']==0 for row in backups.OLD_VALUES)==2
    summary=r.get_production_import_summary(newer)
    assert summary['rows_written']==summary['rows_replaced']==4
    assert summary['rows_inserted']==0 and summary['rows_unchanged']==2 and summary['producer_weeks_replaced']==1
    assert len(r._production)==6 and not old_ids.intersection(r._production.PRODUCTION_ID)
    new_ids=set(prepared.PRODUCTION_ID);state=deepcopy((r._continuity_rows,r._migration_review_audit))
    repeated,again,_,errors,_=stage(r,second)
    assert repeated==newer and set(again.PRODUCTION_ID)==new_ids and not errors
    assert r.commit_staged_production(repeated,'synthetic-staff')==(newer,4)
    assert len(r._production)==6 and len(r.get_production_replacement_backups(newer))==4
    assert (r._continuity_rows,r._migration_review_audit)==state
    assert r._production.PRODUCTION_ID.nunique()==6


def test_snowflake_insert_uses_four_distinct_source_identities_without_connecting():
    raw=read_eims_workbook(BytesIO(workbook(pattern())))
    records,_,_,_=prepare_workbook(raw,'synthetic-file',repository().get_accounts())
    class Executor:
        def executemany(self,sql,params):
            self.sql=sql;self.params=params
            return len(params)
    executor=Executor();repo=SnowflakeRepository()
    assert repo._insert_production(executor,records,'synthetic-batch')==4
    assert len({row[0] for row in executor.params})==4
    source_index=2+PRODUCTION_COLUMNS.index('SOURCE_ROW_NUMBER')
    assert [row[source_index] for row in executor.params]==[50,51,52,53]


@pytest.mark.parametrize('layout',['summary','producer','details','grader'])
@pytest.mark.parametrize('unit',['Dozens','Boxes'])
def test_production_totals_unchanged_when_extra_zero_detail_row_is_present(layout,unit):
    r=repository();raw=read_eims_workbook(BytesIO(workbook(pattern())))
    records,_,_,_=prepare_workbook(raw,'synthetic-file',r.get_accounts())
    kwargs={'layout':layout}
    if layout=='grader':kwargs['grader_key']=next(iter(production_grader_options(records,r.get_accounts(),202601,202601)))
    with_zero,_=build_production_report(records,r.get_accounts(),202601,202601,**kwargs)
    without_extra,_=build_production_report(records.iloc[:3],r.get_accounts(),202601,202601,**kwargs)
    after=production_report_view(with_zero,unit);before=production_report_view(without_extra,unit)
    keys=[column for column in after.columns if column not in AMOUNTS]
    a=after.loc[~after['Row Type'].eq('Data'),[*keys,*AMOUNTS]].reset_index(drop=True)
    b=before.loc[~before['Row Type'].eq('Data'),[*keys,*AMOUNTS]].reset_index(drop=True)
    pd.testing.assert_frame_equal(a,b)
    assert len(with_zero.loc[with_zero['Row Type'].eq('Data')])==4


def test_nest_run_totals_unchanged_with_extra_zero_row():
    r=repository();rows=pattern()
    for row in rows:row['MarketingType']='LB'
    records,_,_,_=prepare_workbook(read_eims_workbook(BytesIO(workbook(rows))),'synthetic-file',r.get_accounts())
    after,_=build_nest_run_report(records,r.get_accounts(),2026,202601,202601)
    before,_=build_nest_run_report(records.iloc[:3],r.get_accounts(),2026,202601,202601)
    for column in NEST_FIELDS:
        assert sum(Decimal(str(value)) for value in after[column] if value!='')==sum(Decimal(str(value)) for value in before[column] if value!='')


@pytest.mark.parametrize('entrypoint',['streamlit_app.py','app/Home.py'])
def test_nonblocking_note_visible_and_import_enabled(entrypoint,tmp_path,monkeypatch):
    root=Path(__file__).parents[1];r=repository();upload=BytesIO(workbook(pattern()));upload.name='synthetic-zero.xlsx'
    app=authenticated_app(root/entrypoint,tmp_path,monkeypatch)
    app.session_state['_base_repo']=r
    monkeypatch.setattr(st,'file_uploader',lambda *a,**k:upload)
    prefix='app/pages/' if entrypoint=='streamlit_app.py' else 'pages/'
    app.switch_page(prefix+'1_Production_Import.py').run()
    assert not app.exception and not app.error
    assert next(metric.value for metric in app.metric if metric.label=='Blocking Errors')=='0'
    assert next(metric.value for metric in app.metric if metric.label=='Warnings')=='1'
    assert any('2 identical all-zero rows were kept (Excel rows 51, 53)' in item.value for item in app.markdown)
    button=next(button for button in app.button if button.label=='Import validated records')
    assert not button.disabled
    button.click().run()
    assert not app.exception and not app.error and len(r._production)==4
