"""Tests for Bolt Optimization: _fast_format_dt date formatting fast-path."""

from datetime import datetime, timezone
from app.models import _fast_format_dt, MIN_DATE, _MIN_DATE_ISO, _game_row_to_dict, _audit_log_row_to_dict


def test_fast_format_dt_min_date():
    """Verify _fast_format_dt short-circuits MIN_DATE and empty values."""
    assert _fast_format_dt(None) == _MIN_DATE_ISO
    assert _fast_format_dt(None, format_dates=False) == MIN_DATE
    assert _fast_format_dt(MIN_DATE) == _MIN_DATE_ISO
    assert _fast_format_dt(MIN_DATE, format_dates=False) == MIN_DATE


def test_fast_format_dt_valid_datetime():
    """Verify _fast_format_dt correctly formats naive and aware datetimes."""
    dt_naive = datetime(2026, 9, 20, 12, 0, 0)
    dt_aware = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)

    assert _fast_format_dt(dt_naive) == "2026-09-20T12:00:00+00:00"
    assert _fast_format_dt(dt_naive, format_dates=False) == dt_aware
    assert _fast_format_dt(dt_aware) == "2026-09-20T12:00:00+00:00"
    assert _fast_format_dt(dt_aware, format_dates=False) == dt_aware


def test_game_row_to_dict_fast_dt():
    """Verify _game_row_to_dict uses _fast_format_dt for created_at and updated_at."""
    class FakeRow:
        def __init__(self, mapping):
            self._mapping = mapping

    row_data = {
        'game_id': 'g1',
        'user_id': 'u1',
        'titulo': 'Test Game',
        'descripcion': 'Desc',
        'imagen_url': None,
        'plataforma': 'PC',
        'estado': 'N/A',
        'categoria': 'Biblioteca',
        'prioridad': 'Media',
        'calificacion': 9,
        'es_favorito': False,
        'created_at': None,
        'updated_at': None,
    }
    fake_row = FakeRow(row_data)

    res = _game_row_to_dict(fake_row)
    assert res['created_at'] == _MIN_DATE_ISO
    assert res['updated_at'] == _MIN_DATE_ISO


def test_audit_log_row_to_dict_fast_dt():
    """Verify _audit_log_row_to_dict uses _fast_format_dt for timestamp."""
    class FakeRow:
        def __init__(self, mapping):
            self._mapping = mapping

    row_data = {
        'audit_id': 'a1',
        'user_id': 'u1',
        'action': 'LOGIN',
        'action_name': 'Inicio de Sesion',
        'resource': 'auth',
        'timestamp': None,
        'ip_address': '127.0.0.1',
        'user_agent': 'pytest',
        'details': {},
        'status': 'SUCCESS',
    }
    fake_row = FakeRow(row_data)

    res = _audit_log_row_to_dict(fake_row)
    assert res['timestamp'] == _MIN_DATE_ISO
