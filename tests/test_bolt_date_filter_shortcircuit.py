from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import parse_date_filter, _ONE_DAY

def test_parse_date_filter_standard():
    dt = parse_date_filter('2026-09-15')
    assert dt == datetime(2026, 9, 15, 0, 0, tzinfo=timezone.utc)

def test_parse_date_filter_end_true():
    dt_start = parse_date_filter('2026-09-15', end=False)
    dt_end = parse_date_filter('2026-09-15', end=True)
    assert dt_end == dt_start + _ONE_DAY
    assert dt_end == datetime(2026, 9, 16, 0, 0, tzinfo=timezone.utc)

def test_parse_date_filter_invalid_inputs():
    assert parse_date_filter('') is None
    assert parse_date_filter(None) is None
    assert parse_date_filter('invalid-date') is None
