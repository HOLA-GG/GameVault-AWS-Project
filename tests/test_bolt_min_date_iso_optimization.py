"""Tests for Bolt Optimization: _MIN_DATE_ISO usage in _user_row_to_dict."""

from datetime import datetime, timezone
from app.models import MIN_DATE, _MIN_DATE_ISO, _user_row_to_dict


class MockMappingRow:
    """Mock row object providing a dictionary _mapping view."""

    def __init__(self, mapping_dict):
        self._mapping = mapping_dict


def test_user_row_to_dict_partial_projection_len_6():
    """Verify _user_row_to_dict for 6-column partial projection (len == 6)."""
    mapping = {
        'user_id': 'user-123',
        'email': 'test@example.com',
        'nombre': 'Test User',
        'prefijo_pais': '+1',
        'telefono': '5551234',
        'role': 'admin',
    }
    row = MockMappingRow(mapping)

    # Test format_dates=True (uses _MIN_DATE_ISO constant)
    res_formatted = _user_row_to_dict(row, format_dates=True)
    assert res_formatted['user_id'] == 'user-123'
    assert res_formatted['email'] == 'test@example.com'
    assert res_formatted['nombre'] == 'Test User'
    assert res_formatted['prefijo_pais'] == '+1'
    assert res_formatted['telefono'] == '5551234'
    assert res_formatted['role'] == 'admin'
    assert res_formatted['created_at'] == _MIN_DATE_ISO
    assert res_formatted['updated_at'] == _MIN_DATE_ISO

    # Test format_dates=False (uses MIN_DATE datetime object)
    res_raw = _user_row_to_dict(row, format_dates=False)
    assert res_raw['created_at'] == MIN_DATE
    assert res_raw['updated_at'] == MIN_DATE


def test_user_row_to_dict_partial_projection_len_3():
    """Verify _user_row_to_dict for 3-column partial projection (len == 3)."""
    mapping = {
        'user_id': 'user-456',
        'email': 'admin@example.com',
        'nombre': 'Admin User',
    }
    row = MockMappingRow(mapping)

    # Test format_dates=True (uses _MIN_DATE_ISO constant)
    res_formatted = _user_row_to_dict(row, format_dates=True)
    assert res_formatted['user_id'] == 'user-456'
    assert res_formatted['email'] == 'admin@example.com'
    assert res_formatted['nombre'] == 'Admin User'
    assert res_formatted['created_at'] == _MIN_DATE_ISO
    assert res_formatted['updated_at'] == _MIN_DATE_ISO

    # Test format_dates=False (uses MIN_DATE datetime object)
    res_raw = _user_row_to_dict(row, format_dates=False)
    assert res_raw['created_at'] == MIN_DATE
    assert res_raw['updated_at'] == MIN_DATE
