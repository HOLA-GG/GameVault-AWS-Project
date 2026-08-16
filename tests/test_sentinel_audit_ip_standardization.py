import pytest
import os
import sys

@pytest.fixture
def app(monkeypatch, tmp_path):
    db_file = tmp_path / "gamevault_test_ip_std.db"

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    yield flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_audit_log_uses_get_request_ip(client, app):
    """Verify that audit logs created during route invocation use get_request_ip() instead of raw request.remote_addr."""
    response = client.post(
        '/login',
        data={'email': 'nonexistent@example.com', 'password': 'WrongPassword123!'},
        environ_base={'REMOTE_ADDR': '203.0.113.195'}
    )
    assert response.status_code == 302

    from app.models import get_session_factory, AuditLog, select
    session_factory = get_session_factory()
    with session_factory() as session:
        logs = session.scalars(
            select(AuditLog)
            .where(AuditLog.action == 'FAILED_LOGIN', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(logs) > 0
        latest_log = logs[0]
        assert latest_log.ip_address == '203.0.113.195'
