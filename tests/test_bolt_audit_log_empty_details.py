"""
tests/test_bolt_audit_log_empty_details.py - Verifies the performance optimization and correctness
of crear_log_audit when details is empty, None, or populated with sensitive/non-sensitive data.
"""

import os
import uuid
import pytest
from app import create_app
from app.models import crear_usuario, crear_log_audit, obtener_todos_logs


@pytest.fixture
def app(monkeypatch):
    db_file = f"test_bolt_audit_log_empty_details_{uuid.uuid4().hex}.db"
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    flask_app = create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass


def test_crear_log_audit_empty_details(app):
    """Verifies that crear_log_audit correctly creates an audit log when details is empty or None."""
    with app.app_context():
        email = f"user1_{uuid.uuid4().hex}@example.com"
        user = crear_usuario('Test User 1', '', email, '', '', 'hash12345')
        assert user is not None
        user_id = user['user_id']

        # Test None details
        res_none = crear_log_audit(
            user_id=user_id,
            action='LOGIN',
            resource='auth',
            details=None,
        )
        assert res_none['success'] is True
        assert res_none['audit_id'] is not None

        # Test empty dict details
        res_empty = crear_log_audit(
            user_id=user_id,
            action='LOGOUT',
            resource='auth',
            details={},
        )
        assert res_empty['success'] is True
        assert res_empty['audit_id'] is not None

        logs = obtener_todos_logs({'user_id': user_id})
        assert len(logs) == 2
        for log in logs:
            assert isinstance(log['details'], dict)
            assert log['details'] == {}


def test_crear_log_audit_populated_sensitive_details(app):
    """Verifies that crear_log_audit redacts sensitive details when details is populated."""
    with app.app_context():
        email = f"user2_{uuid.uuid4().hex}@example.com"
        user = crear_usuario('Test User 2', '', email, '', '', 'hash12345')
        assert user is not None
        user_id = user['user_id']

        res = crear_log_audit(
            user_id=user_id,
            action='LOGIN',
            resource='auth',
            details={'email': email, 'password': 'SecretPassword123', 'status': 'ok'},
        )
        assert res['success'] is True

        logs = obtener_todos_logs({'user_id': user_id})
        assert len(logs) == 1
        details = logs[0]['details']
        assert details['email'] == email
        assert details['password'] == '[REDACTED]'
        assert details['status'] == 'ok'


def test_crear_log_audit_request_id_injection(app):
    """Verifies that request_id in Flask g is correctly injected into safe_details."""
    with app.test_request_context():
        email = f"user3_{uuid.uuid4().hex}@example.com"
        user = crear_usuario('Test User 3', '', email, '', '', 'hash12345')
        assert user is not None
        user_id = user['user_id']

        from flask import g
        g.request_id = 'req-123456789'

        res = crear_log_audit(
            user_id=user_id,
            action='CREATE_GAME',
            resource='games',
            details=None,
        )
        assert res['success'] is True

        logs = obtener_todos_logs({'user_id': user_id})
        assert len(logs) == 1
        assert logs[0]['details'] == {'request_id': 'req-123456789'}
