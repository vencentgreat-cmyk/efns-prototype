"""Read-only batch replacement evidence and plain import summaries."""
import streamlit as st
from data.source_evidence import evidence_json
from app.ui import show_data_error


def summary_text(summary):
    span = f"{summary['week_start']} to {summary['week_end']}" if summary.get('week_start') else 'none'
    return (f"Batch {summary['import_id']}: {summary['rows_inserted']} rows inserted for new producer-weeks; "
        f"{summary['rows_replaced']} old rows replaced; {summary['producer_weeks_replaced']} producer-weeks replaced "
        f"(weeks {span}); {summary['rows_written']} uploaded rows saved; {summary['rows_unchanged']} rows unchanged.")


def render_import_summary(summary):
    if summary:
        st.success(summary_text(summary).removeprefix(f"Batch {summary['import_id']}: "))
        with st.expander("Batch reference", expanded=False):
            st.code(str(summary["import_id"]), language=None)
    else:
        st.info('This batch predates the producer-week replacement summary. See its retained source and history.')


def render_past_replacements(repo):
    with st.expander('Replaced values from a past import',expanded=False):
        batch = st.text_input('Import Batch ID',key='production_backup_batch')
        if st.button('View replaced values',disabled=not batch.strip(),key='production_backup_view'):
            try:
                render_import_summary(repo.get_production_import_summary(batch.strip()))
                rows=repo.get_production_replacement_backups(batch.strip())
                if rows.empty:
                    st.info('No replaced values were recorded for this batch.')
                else:
                    display=rows.copy()
                    for column in ('OLD_VALUES','SIZE_BREAKDOWN_ROWS'):
                        if column in display:
                            display[column]=display[column].map(lambda value:evidence_json(value) if isinstance(value,(dict,list)) else value)
                    st.dataframe(display.rename(columns={'PRODUCTION_ID':'Previous Production ID',
                        'PRODUCER_ACCOUNT_ID':'Producer Account ID','SOURCE_WEEK_CODE':'Week',
                        'REPLACED_BY':'Replaced By','REPLACED_AT':'Replaced On','OLD_VALUES':'Previous Values',
                        'SIZE_BREAKDOWN_ROWS':'Previous Size Breakdown'}),hide_index=True,width='stretch')
                    st.caption('Read-only evidence. Restoring a batch requires a reviewed correction; there is no restore action here.')
            except Exception as exc:
                show_data_error(exc)
