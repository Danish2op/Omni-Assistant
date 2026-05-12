import os
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    # Python < 3.9 fallback if needed
    import pytz
    ZoneInfo = pytz.timezone

IST_TZ = "Asia/Kolkata"

def get_ist_timezone():
    try:
        return ZoneInfo(IST_TZ)
    except Exception:
        import pytz
        return pytz.timezone(IST_TZ)

def get_current_ist_time() -> datetime:
    """Returns the current time in IST timezone."""
    return datetime.now(get_ist_timezone())

def format_ist_time(dt: datetime = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """Returns the formatted current time in IST, or formats a given datetime in IST."""
    if dt is None:
        dt = get_current_ist_time()
    else:
        # if dt is naive, assume it's UTC or local? Best to keep it aware.
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt = dt.astimezone(get_ist_timezone())
    return dt.strftime(format_str)
