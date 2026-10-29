"""Review witness, not a repair: expose equal-version Mock clock collisions."""
import datetime as dt
import pandas as pd
import pytest
import data.repositories.mock as mock
from data.repositories.base import ConcurrencyError
from tests.test_staff_workflows import chain
from tests.test_account_usage_quantity import ACTOR,current
from app.security import DEFAULT_USER_SEEDS,verify_password,generate_temporary_password


def test_review_seed_sentinels_cannot_authenticate():
    assert len(DEFAULT_USER_SEEDS)==4
    for seed in DEFAULT_USER_SEEDS:
        assert seed.password_hash == 'pbkdf2_sha256$600000$REVIEW_DISABLED$REVIEW_DISABLED'
        assert not verify_password(generate_temporary_password(),seed.password_hash)


def test_equal_clock_version_cannot_authorize_a_stale_quantity_request(chain,monkeypatch):
    r,a,o,f,q,fid,record=chain
    fixed=dt.datetime.now(dt.timezone.utc)
    RealDateTime=dt.datetime
    class FixedDateTime(RealDateTime):
        @classmethod
        def now(cls,tz=None):
            return fixed.astimezone(tz) if tz else fixed.replace(tzinfo=None)
    r._flocks.loc[r._flocks.FLOCK_ID==fid,'UPDATED_AT']=pd.Timestamp(fixed)
    old=r.get_flock(fid)['UPDATED_AT']
    monkeypatch.setattr(mock.dt,'datetime',FixedDateTime)
    current(r,fid,'Count',15,'review-first-request')
    assert pd.Timestamp(r.get_flock(fid)['UPDATED_AT'])>pd.Timestamp(old)
    request=dict(FLOCK_ID=fid,TRANSACTION_TYPE='Removal',QUANTITY=3,TRANSACTION_DATE=dt.date.today())
    with pytest.raises(ConcurrencyError):
        r.record_current_flock_quantity(request,'review-stale-request',old,'Synthetic distinct request with stale token',confirmed=True,actor=ACTOR, expected_bird_count=(r.get_flock((request).get('FLOCK_ID')) or {}).get('BIRD_COUNT'))
