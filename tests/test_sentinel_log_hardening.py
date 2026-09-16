import pytest
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app_with_db(monkeypatch):
    db_file = 'gamevault_test_hardening.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    # Force reload of app and models
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({"TESTING": True, "WTF_CSRF_ENABLED": False})

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

def test_crear_reset_token_ip_truncation(app_with_db):
    from app.models import crear_usuario, crear_reset_token, get_session_factory, PasswordResetToken, select

    with app_with_db.app_context():
        user = crear_usuario("Test", "User", "longip@example.com", "", "", "hash")

        # Invalid IP should be converted to 'unknown'
        long_ip = "a" * 100
        result = crear_reset_token(user['user_id'], ip_address=long_ip)
        assert result['success'] is True

        # Valid IPv4 with port should be normalized
        result_v4_port = crear_reset_token(user['user_id'], ip_address='127.0.0.1:8080')
        assert result_v4_port['success'] is True

        # Valid IPv6 with port should be normalized
        result_v6_port = crear_reset_token(user['user_id'], ip_address='[::1]:8080')
        assert result_v6_port['success'] is True

        # Verify in DB
        session_factory = get_session_factory()
        with session_factory() as session:
            # 1. Check invalid IP
            token1 = session.scalar(select(PasswordResetToken).where(PasswordResetToken.user_id == user['user_id']).order_by(PasswordResetToken.created_at.asc()).limit(1))
            assert token1.ip_address == 'unknown'

            # 2. Check normalized IPv4 with port
            # (get the latest token since we created v4_port and v6_port)
            tokens = session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user['user_id']).order_by(PasswordResetToken.created_at.desc())).all()
            assert tokens[0].ip_address == '::1'
            assert tokens[1].ip_address == '127.0.0.1'


def test_ip_address_html_escaping(app_with_db):
    from app.routes import enviar_email_reset_password
    from unittest.mock import patch

    with app_with_db.app_context():
        # Override MAIL_SUPPRESS_SEND temporarily
        app_with_db.config['MAIL_SUPPRESS_SEND'] = False

        # Use test_request_context to allow url_for to build URLs
        with app_with_db.test_request_context():
            # We mock mail.send to inspect the HTML content of the message
            with patch('app.routes.mail.send') as mock_send:
                enviar_email_reset_password(
                    destinatario='test@example.com',
                    token='dummy-token',
                    ip_address='<script>alert("XSS")</script>'
                )
                assert mock_send.called
                sent_msg = mock_send.call_args[0][0]
                # Ensure HTML is escaped and the raw script tag is not present
                assert '<script>' not in sent_msg.html
                assert '&lt;script&gt;' in sent_msg.html

def test_crear_log_audit_field_truncation(app_with_db):
    from app.models import crear_log_audit, get_session_factory, AuditLog, select

    with app_with_db.app_context():
        long_action = "A" * 100
        long_action_name = "N" * 150
        long_resource = "R" * 100

        result = crear_log_audit(
            user_id=None,
            action=long_action,
            resource=long_resource,
            status="SUCCESS"
        )
        # Note: action_name is derived from action if not provided

        assert result['success'] is True

        session_factory = get_session_factory()
        with session_factory() as session:
            log = session.scalar(select(AuditLog).where(AuditLog.audit_id == result['audit_id']))
            assert len(log.action) <= 80
            assert log.action == "A" * 80
            assert len(log.resource) <= 80
            assert log.resource == "R" * 80
            # action_name should also be truncated if it was derived or passed long
            assert len(log.action_name) <= 120

def test_crear_log_audit_details_redaction(app_with_db):
    from app.models import crear_log_audit, get_session_factory, AuditLog, select

    with app_with_db.app_context():
        details = {
            "password": "secret_password",
            "new_password": "new_secret",
            "token": "sensitive_token",
            "reset_token": "another_token",
            "secret_key": "very_secret",
            "api_hash": "some_hash",
            "safe_field": "public_data"
        }

        result = crear_log_audit(
            user_id=None,
            action="TEST_REDACTION",
            resource="test",
            details=details
        )

        session_factory = get_session_factory()
        with session_factory() as session:
            log = session.scalar(select(AuditLog).where(AuditLog.audit_id == result['audit_id']))
            redacted_details = log.details

            assert redacted_details["password"] == "[REDACTED]"
            assert redacted_details["new_password"] == "[REDACTED]"
            assert redacted_details["token"] == "[REDACTED]"
            assert redacted_details["reset_token"] == "[REDACTED]"
            assert redacted_details["secret_key"] == "[REDACTED]"
            assert redacted_details["api_hash"] == "[REDACTED]"
            assert redacted_details["safe_field"] == "public_data"
