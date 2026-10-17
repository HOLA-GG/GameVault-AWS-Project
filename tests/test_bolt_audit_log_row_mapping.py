"""
tests/test_bolt_audit_log_row_mapping.py

Verifica la optimización de mapeo rápido con indexación directa por corchetes (EAFP)
para proyecciones SQL de 9 columnas en AuditLog y User.
"""

from __future__ import annotations

from datetime import datetime, timezone
from app.models import _audit_log_row_to_dict, _user_row_to_dict, MIN_DATE, _MIN_DATE_ISO


class MockRowMapping:
    def __init__(self, mapping_dict):
        self._mapping = mapping_dict


def test_audit_log_row_to_dict_9_columns_fast_path():
    """Verifica que la proyección selective de 9 columnas en AuditLog use el camino rápido sin KeyError."""
    now = datetime.now(timezone.utc)
    raw_mapping = {
        'audit_id': 'audit-123',
        'user_id': 'user-456',
        'action': 'LOGIN',
        'action_name': 'Inicio de sesión',
        'resource': 'auth',
        'timestamp': now,
        'ip_address': '127.0.0.1',
        'details': {'method': 'password'},
        'status': 'SUCCESS',
    }

    mock_row = MockRowMapping(raw_mapping)
    res = _audit_log_row_to_dict(mock_row, format_dates=False)

    assert res['audit_id'] == 'audit-123'
    assert res['user_id'] == 'user-456'
    assert res['action'] == 'LOGIN'
    assert res['action_name'] == 'Inicio de sesión'
    assert res['resource'] == 'auth'
    assert res['timestamp'] == now
    assert res['ip_address'] == '127.0.0.1'
    assert res['user_agent'] == 'unknown'
    assert res['details'] == {'method': 'password'}
    assert res['status'] == 'SUCCESS'


def test_user_row_to_dict_9_columns_fast_path():
    """Verifica que la proyección selective de 9 columnas en User use el camino rápido sin KeyError."""
    raw_mapping = {
        'user_id': 'user-789',
        'email': 'user@example.com',
        'nombre': 'Jules',
        'apellido': 'Engineer',
        'prefijo_pais': '+1',
        'telefono': '5551234',
        'role': 'user',
        'status': 'active',
        'collection_visibility': 'public',
    }

    mock_row = MockRowMapping(raw_mapping)
    res = _user_row_to_dict(mock_row, format_dates=False)

    assert res['user_id'] == 'user-789'
    assert res['email'] == 'user@example.com'
    assert res['nombre'] == 'Jules'
    assert res['apellido'] == 'Engineer'
    assert res['prefijo_pais'] == '+1'
    assert res['telefono'] == '5551234'
    assert res['password_hash'] == ''
    assert res['role'] == 'user'
    assert res['status'] == 'active'
    assert res['collection_visibility'] == 'public'
    assert res['homepage_showcase_opt_in'] is False
    assert res['created_at'] == MIN_DATE
    assert res['updated_at'] == MIN_DATE
