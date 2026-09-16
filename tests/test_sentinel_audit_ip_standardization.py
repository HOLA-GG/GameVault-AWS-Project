import os
import sys
import logging
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_ip_standardization.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": True,
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_csrf_error_handler_ip_sanitization(client, app):
    """Verifica que handle_csrf_error sanitiza la dirección IP de la solicitud."""
    response = client.post('/login', environ_base={'REMOTE_ADDR': '127.0.0.1:8080'})
    assert response.status_code == 400

    from app.models import get_session_factory, AuditLog, select
    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == 'CSRF_FAILURE')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.ip_address == '127.0.0.1'

def test_after_request_ip_sanitization(client, app, caplog):
    """Verifica que log_request sanitiza la dirección IP en los logs del servidor."""
    app.logger.propagate = True
    with caplog.at_level(logging.INFO, logger=app.logger.name):
        response = client.get('/healthz', environ_base={'REMOTE_ADDR': '192.168.1.50; injection_attempt'})
        assert response.status_code == 200
        assert 'remote_addr=unknown' in caplog.text
        assert 'injection_attempt' not in caplog.text
