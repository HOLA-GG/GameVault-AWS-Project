import pytest
from app.routes import build_admin_log_groups


def test_build_admin_log_groups_empty():
    assert build_admin_log_groups([]) == []


def test_build_admin_log_groups_single_user():
    logs = [
        {
            'audit_id': 'a1',
            'user_id': 'u1',
            'action': 'LOGIN',
            'action_name': 'Inicio de sesión',
            'resource': 'auth',
            'timestamp': '2026-01-01T00:00:00Z',
            'ip_address': '127.0.0.1',
            'details': {},
            'status': 'SUCCESS',
        },
        {
            'audit_id': 'a2',
            'user_id': 'u1',
            'action': 'LOGOUT',
            'action_name': 'Cierre de sesión',
            'resource': 'auth',
            'timestamp': '2026-01-01T01:00:00Z',
            'ip_address': '127.0.0.1',
            'details': {},
            'status': 'SUCCESS',
        },
    ]

    groups = build_admin_log_groups(logs)
    assert len(groups) == 1
    g = groups[0]
    assert g['user_id'] == 'u1'
    assert g['events_count'] == 2
    assert len(g['items']) == 2
    assert g['latest_timestamp'] == '2026-01-01T00:00:00Z'
    assert g['latest_action'] == 'Inicio de sesión'


def test_build_admin_log_groups_multiple_users_and_system():
    logs = [
        {
            'audit_id': 'a1',
            'user_id': 'u1',
            'action': 'LOGIN',
            'action_name': 'Inicio de sesión',
            'timestamp': '2026-01-01T02:00:00Z',
        },
        {
            'audit_id': 'a2',
            'user_id': None,
            'action': 'SYSTEM_CRON',
            'action_name': None,
            'timestamp': '2026-01-01T01:00:00Z',
        },
        {
            'audit_id': 'a3',
            'user_id': 'u2',
            'action': 'CREATE_GAME',
            'action_name': 'Crear juego',
            'timestamp': '2026-01-01T00:00:00Z',
        },
        {
            'audit_id': 'a4',
            'user_id': 'u1',
            'action': 'UPDATE_PROFILE',
            'action_name': 'Actualizar perfil',
            'timestamp': '2026-01-01T00:30:00Z',
        },
    ]

    groups = build_admin_log_groups(logs)
    assert len(groups) == 3

    # Fast lookup by user_id
    by_user = {g['user_id']: g for g in groups}

    assert 'u1' in by_user
    assert by_user['u1']['events_count'] == 2
    assert by_user['u1']['latest_action'] == 'Inicio de sesión'

    assert 'system' in by_user
    assert by_user['system']['events_count'] == 1
    assert by_user['system']['email'] == 'sistema@local'
    assert by_user['system']['nombre'] == 'Sistema'
    assert by_user['system']['latest_action'] == 'SYSTEM_CRON'

    assert 'u2' in by_user
    assert by_user['u2']['events_count'] == 1
    assert by_user['u2']['latest_action'] == 'Crear juego'
