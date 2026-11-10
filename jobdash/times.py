"""Time helpers. The database stores UTC; the dashboard shows Central time."""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pandas as pd

LOCAL_TZ_NAME = "America/Chicago"
LOCAL = ZoneInfo(LOCAL_TZ_NAME)


def now_local() -> datetime:
    return datetime.now(LOCAL)


def to_local(dt: datetime | None) -> datetime | None:
    if dt is None or pd.isna(dt):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(LOCAL)


def local_to_utc(d: date, t: time) -> datetime:
    """A date + time picked in the UI (Central) -> aware UTC datetime."""
    return datetime.combine(d, t, tzinfo=LOCAL).astimezone(timezone.utc)


def fmt(dt: datetime | None, pattern: str = "%a %b %d, %I:%M %p") -> str:
    local = to_local(dt)
    if local is None:
        return "—"
    return local.strftime(pattern).replace(" 0", " ")


def fmt_date(d) -> str:
    if d is None or pd.isna(d):
        return "—"
    if isinstance(d, datetime):
        d = to_local(d)
    return d.strftime("%b %d, %Y").replace(" 0", " ")


def localize_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Convert UTC timestamp columns of a DataFrame to Central time."""
    for col in columns:
        if col in df.columns and not df.empty:
            df[col] = pd.to_datetime(df[col], utc=True).dt.tz_convert(LOCAL_TZ_NAME)
    return df
