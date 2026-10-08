from datetime import datetime, timezone
import pytest
from app.models import _user_row_to_dict, MIN_DATE, _MIN_DATE_ISO, User


class MockMappingRow:
    def __init__(self, mapping_dict):
        self._mapping = mapping_dict


def test_user_row_to_dict_full_row_fast_dt():
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    full_dict = {
        'user_id': 'usr_1',
        'email': 'user1@example.com',
        'nombre': 'User1',
        'apellido': 'Test',
        'prefijo_pais': '+1',
        'telefono': '1234567890',
        'password_hash': 'hash123',
        'role': 'user',
        'status': 'active',
        'collection_visibility': 'public',
        'homepage_showcase_opt_in': True,
        'created_at': MIN_DATE,
        'updated_at': now,
    }

    row = MockMappingRow(full_dict)

    # Test format_dates=True
    res_formatted = _user_row_to_dict(row, format_dates=True)
    assert res_formatted['user_id'] == 'usr_1'
    assert res_formatted['created_at'] == _MIN_DATE_ISO
    assert res_formatted['updated_at'] == '2026-09-20T12:00:00+00:00'

    # Test format_dates=False
    res_raw = _user_row_to_dict(row, format_dates=False)
    assert res_raw['created_at'] == MIN_DATE
    assert res_raw['updated_at'] == now


def test_user_row_to_dict_partial_projections():
    # 6 columns projection
    dict_6 = {
        'user_id': 'usr_6',
        'email': 'user6@example.com',
        'nombre': 'User6',
        'prefijo_pais': '+1',
        'telefono': '123',
        'role': 'admin',
    }
    res_6 = _user_row_to_dict(MockMappingRow(dict_6), format_dates=True)
    assert res_6['user_id'] == 'usr_6'
    assert res_6['created_at'] == _MIN_DATE_ISO

    # 3 columns projection
    dict_3 = {
        'user_id': 'usr_3',
        'email': 'user3@example.com',
        'nombre': 'User3',
    }
    res_3 = _user_row_to_dict(MockMappingRow(dict_3), format_dates=True)
    assert res_3['user_id'] == 'usr_3'
    assert res_3['created_at'] == _MIN_DATE_ISO


def test_user_row_to_dict_fallback_and_orm():
    now = datetime(2026, 9, 20, 15, 30, 0, tzinfo=timezone.utc)
    fallback_dict = {
        'user_id': 'usr_fb',
        'email': 'fb@example.com',
        'nombre': 'Fallback',
        'created_at': None,
        'updated_at': now,
    }
    res_fb = _user_row_to_dict(MockMappingRow(fallback_dict), format_dates=True)
    assert res_fb['user_id'] == 'usr_fb'
    assert res_fb['created_at'] == _MIN_DATE_ISO
    assert res_fb['updated_at'] == '2026-09-20T15:30:00+00:00'

    # ORM User object
    user_obj = User(
        user_id='usr_orm',
        email='orm@example.com',
        nombre='ORM User',
        created_at=MIN_DATE,
        updated_at=now,
    )
    res_orm = _user_row_to_dict(user_obj, format_dates=True)
    assert res_orm['user_id'] == 'usr_orm'
    assert res_orm['created_at'] == _MIN_DATE_ISO
    assert res_orm['updated_at'] == '2026-09-20T15:30:00+00:00'
