from copy import deepcopy
from pathlib import Path

import pytest

from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository


@pytest.mark.parametrize('batch_id', [
    'DEV_MIGRATION_REAL_HISTORY', 'DEV_MIGRATION_SYNTHETIC_EXAMPLE', 'other', None,
])
def test_prefix_never_authorizes_automatic_cleanup(batch_id):
    mock=MockRepository()
    mock._migration_batches=[{'MIGRATION_BATCH_ID':batch_id,'STATUS':'COMMITTED'}]
    mock._migration_raw_rows=[{'MIGRATION_BATCH_ID':batch_id,'MIGRATION_RAW_ROW_ID':'source'}]
    before=deepcopy((mock._migration_batches,mock._migration_raw_rows))
    with pytest.raises(ValueError,match='cleanup is disabled'):
        mock.cleanup_synthetic_migration(batch_id)
    assert (mock._migration_batches,mock._migration_raw_rows)==before
    # An unusable executor proves no SQL CALL/REMOVE/transaction is attempted.
    snowflake=SnowflakeRepository(executor=object())
    with pytest.raises(Exception,match='cleanup is disabled'):
        snowflake.cleanup_synthetic_migration(batch_id)


def test_cleanup_ddl_preserves_signature_and_grants_but_has_no_data_actions():
    sql=Path('sql/15_Block_Unverified_Migration_Cleanup.sql').read_text().upper()
    assert 'COPY GRANTS' in sql
    assert 'REJECTED_MANUAL_PROVENANCE_REVIEW_REQUIRED' in sql
    for statement in ('DELETE FROM','REMOVE ','TRUNCATE','DROP TABLE','CALL '):
        assert statement not in sql
