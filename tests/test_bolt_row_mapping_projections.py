"""Test selective projection mapping optimizations in _user_row_to_dict and _audit_log_row_to_dict."""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import (
    _user_row_to_dict,
    _audit_log_row_to_dict,
    MIN_DATE,
    utcnow,
)


class MockRow:
    """Simula un objeto Row de SQLAlchemy con un atributo _mapping dict-like."""
    def __init__(self, mapping_dict):
        self._mapping = mapping_dict


def test_user_row_to_dict_selective_projections_direct():
    """Verifica que _user_row_to_dict maneje rápida y correctamente proyecciones de 13, 6 y 3 campos."""
    now_dt = utcnow()

    # Full row (len 13)
    full_mapping = {
        'user_id': 'u_full',
        'email': 'full@test.com',
        'nombre': 'Full User',
        'apellido': 'Smith',
        'prefijo_pais': '+1',
        'telefono': '5551234',
        'password_hash': 'hash123',
        'role': 'admin',
        'status': 'active',
        'collection_visibility': 'public',
        'homepage_showcase_opt_in': True,
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    u_full = _user_row_to_dict(MockRow(full_mapping), format_dates=False)
    assert u_full['user_id'] == 'u_full'
    assert u_full['email'] == 'full@test.com'
    assert u_full['role'] == 'admin'
    assert u_full['homepage_showcase_opt_in'] is True

    # 6-field projection (admin_panel)
    mapping_6 = {
        'user_id': 'u_6',
        'email': 'six@test.com',
        'nombre': 'Six User',
        'prefijo_pais': '+34',
        'telefono': '600000000',
        'role': 'user',
    }
    u6 = _user_row_to_dict(MockRow(mapping_6), format_dates=False)
    assert u6['user_id'] == 'u_6'
    assert u6['email'] == 'six@test.com'
    assert u6['nombre'] == 'Six User'
    assert u6['prefijo_pais'] == '+34'
    assert u6['telefono'] == '600000000'
    assert u6['role'] == 'user'
    assert u6['status'] == 'active'

    # 3-field projection (admin_logs user_map)
    mapping_3 = {
        'user_id': 'u_3',
        'email': 'three@test.com',
        'nombre': 'Three User',
    }
    u3 = _user_row_to_dict(MockRow(mapping_3), format_dates=False)
    assert u3['user_id'] == 'u_3'
    assert u3['email'] == 'three@test.com'
    assert u3['nombre'] == 'Three User'


def test_audit_log_row_to_dict_selective_projections_direct():
    """Verifica que _audit_log_row_to_dict maneje rápida y correctamente proyecciones de 10 y 9 campos."""
    now_dt = utcnow()

    # Full audit log row (len 10)
    full_log_mapping = {
        'audit_id': 'log_10',
        'user_id': 'u1',
        'action': 'LOGIN',
        'action_name': 'Inicio de sesión',
        'resource': 'auth',
        'timestamp': now_dt,
        'ip_address': '192.168.1.1',
        'user_agent': 'Mozilla/5.0',
        'details': {'key': 'val'},
        'status': 'SUCCESS',
    }
    l10 = _audit_log_row_to_dict(MockRow(full_log_mapping), format_dates=False)
    assert l10['audit_id'] == 'log_10'
    assert l10['action'] == 'LOGIN'
    assert l10['user_agent'] == 'Mozilla/5.0'

    # 9-field projection (admin_logs)
    log_9_mapping = {
        'audit_id': 'log_9',
        'user_id': 'u1',
        'action': 'LOGIN',
        'action_name': 'Inicio de sesión',
        'resource': 'auth',
        'timestamp': now_dt,
        'ip_address': '192.168.1.1',
        'details': {'key': 'val'},
        'status': 'SUCCESS',
    }
    l9 = _audit_log_row_to_dict(MockRow(log_9_mapping), format_dates=False)
    assert l9['audit_id'] == 'log_9'
    assert l9['action'] == 'LOGIN'
    assert l9['ip_address'] == '192.168.1.1'
    assert l9['user_agent'] == 'unknown'
