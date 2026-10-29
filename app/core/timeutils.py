from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from app.core.config import settings


def tz() -> ZoneInfo:
    return ZoneInfo(settings.TIMEZONE)


def local_now() -> datetime:
    return datetime.now(tz())


def local_today() -> date:
    return local_now().date()


def day_start(day: date) -> datetime:
    """First instant of a business-timezone day, as a UTC datetime (what the database compares against)."""
    return datetime.combine(day, time.min, tzinfo=tz()).astimezone(timezone.utc)


def day_end(day: date) -> datetime:
    """Last instant of a business-timezone day, as a UTC datetime."""
    return datetime.combine(day, time.max, tzinfo=tz()).astimezone(timezone.utc)


def local_date(moment: datetime) -> date:
    """The calendar day (in the business timezone) a stored timestamp belongs to."""
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=ZoneInfo("UTC"))
    return moment.astimezone(tz()).date()


def months_back(first_of_month: date, count: int) -> list[str]:
    """`count` YYYY-MM keys ending with the month of `first_of_month`, oldest first."""
    keys: list[str] = []
    cur = first_of_month.replace(day=1)
    for _ in range(count):
        keys.append(cur.strftime("%Y-%m"))
        cur = (cur - timedelta(days=1)).replace(day=1)
    return list(reversed(keys))
