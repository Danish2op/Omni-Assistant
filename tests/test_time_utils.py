import pytest
from datetime import datetime, timezone
try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from app.core.time_utils import get_current_ist_time, format_ist_time

def test_get_current_ist_time():
    now_ist = get_current_ist_time()
    assert now_ist.tzinfo is not None
    assert now_ist.tzinfo.key == "Asia/Kolkata"

def test_format_ist_time():
    dt = datetime(2026, 5, 11, 12, 0, 0, tzinfo=timezone.utc)
    # 12:00 UTC is 17:30 IST
    formatted = format_ist_time(dt)
    assert formatted == "2026-05-11 17:30:00"
