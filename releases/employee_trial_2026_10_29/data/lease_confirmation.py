"""Acknowledgement of retrospective report changes; never a quota calculation."""
import datetime as dt
from data.position_evidence import day
from data.repositories.base import RepositoryError

REPORT_CHANGE_WARNING = 'Figures in reports already produced for this period will change.'


def confirmation_required(business_date):
    from data.business_time import halifax_today
    when=day(business_date)
    return when is not None and when<halifax_today()


def report_change_confirmation(business_date, confirmed, actor):
    required=confirmation_required(business_date)
    if required and confirmed is not True:
        raise RepositoryError('Confirm that figures in reports already produced for this period will change before saving this past-date lease correction.')
    return {'required':required,'confirmed':confirmed is True,
        'business_date':str(day(business_date)),
        'confirmed_by':actor.get('user_id') if confirmed is True else None,
        'confirmed_at':dt.datetime.now(dt.timezone.utc).isoformat() if confirmed is True else None}
