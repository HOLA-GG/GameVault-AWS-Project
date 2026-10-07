from datetime import datetime, timezone
from app.models import MIN_DATE, _MIN_DATE_ISO, as_iso


def test_as_iso_none():
    assert as_iso(None) is None


def test_as_iso_min_date():
    assert as_iso(MIN_DATE) == _MIN_DATE_ISO


def test_as_iso_aware_datetime():
    dt = datetime(2026, 3, 15, 12, 30, 45, tzinfo=timezone.utc)
    assert as_iso(dt) == "2026-03-15T12:30:45+00:00"


def test_as_iso_naive_datetime():
    dt = datetime(2026, 3, 15, 12, 30, 45)
    assert as_iso(dt) == "2026-03-15T12:30:45+00:00"
