"""Every interface/concrete public method needs a rule or a reviewed narrow exception."""
import inspect
import pytest
from app.services.authorized_repository import AuthorizedRepository
from data.repositories.base import BaseRepository
from data.repositories.mock import MockRepository
from data.repositories.snowflake import SnowflakeRepository
from tests.test_report_center import user

# Read-only preview/validation, or append-only history called inside guarded imports.
PASSTHROUGH_ALLOWLIST = frozenset({
    'preview_historical_corrections',
    'check_facility_history',
    'check_facility_ownership',
    'check_flock_reference_change',
    'append_operational_flock_revision',
})


def assert_authorization_coverage(repo):
    names={name for cls in (BaseRepository,type(repo))
        for name,method in inspect.getmembers(cls) if not name.startswith('_') and callable(method)}
    proxy=AuthorizedRepository(repo,object(),user())
    passthrough={name for name in names if getattr(proxy,name)==getattr(repo,name)}
    # Comparing callable identity also handles already-decorated base methods;
    # merely checking __wrapped__ would incorrectly bless an unguarded decorator.
    assert not passthrough-PASSTHROUGH_ALLOWLIST, f'Uncovered repository methods: {sorted(passthrough-PASSTHROUGH_ALLOWLIST)}'
    assert passthrough==PASSTHROUGH_ALLOWLIST, 'Remove obsolete exceptions once a method gets an explicit rule.'


@pytest.mark.parametrize('repository',[MockRepository,SnowflakeRepository])
def test_every_public_repository_method_has_authorization_rule(repository):
    assert_authorization_coverage(repository())  # No method body or database call is invoked.


def test_a_new_unguarded_interface_writer_is_detected(monkeypatch):
    def unguarded_write(self):pytest.fail('Coverage must not invoke repository writes')
    monkeypatch.setattr(BaseRepository,'unguarded_write',unguarded_write,raising=False)
    with pytest.raises(AssertionError,match='unguarded_write'):
        assert_authorization_coverage(MockRepository())
