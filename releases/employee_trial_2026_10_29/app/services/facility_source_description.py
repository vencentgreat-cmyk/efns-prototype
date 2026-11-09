"""Read-only source evidence block shared by the Facility page and AppTest."""
from app.security import AuthorizationError
from data.repositories.base import RepositoryError


def render_source_description(st,repo,facility_id):
    with st.expander('Original migration source description'):
        st.caption('Retained historical source evidence, not the current maintained description or Comments. No values are copied into the Facility record.')
        try:
            rows=repo.get_facility_source_descriptions(facility_id)
        except AuthorizationError:
            st.info('Import review permission is required to view original migration descriptions.')
            return
        except RepositoryError as err:
            if isinstance(err.__cause__,AuthorizationError):
                st.info('Import review permission is required to view original migration descriptions.')
                return
            st.warning(str(err))
            return
        if rows.empty:
            st.info('No verified original migration description is available for this Facility.')
            return
        for row in rows.to_dict('records'):
            st.text(row['DESCRIPTION'])
            st.caption(f"Original migration source · {row['SOURCE_FILENAME']} · source row {row['SOURCE_ROW_NUMBER']} · batch {row['MIGRATION_BATCH_ID']} · RAW row {row['MIGRATION_RAW_ROW_ID']}")
            st.caption('Source field: efc_facilitydescription · file SHA-256: '+row['FILE_SHA256'])
