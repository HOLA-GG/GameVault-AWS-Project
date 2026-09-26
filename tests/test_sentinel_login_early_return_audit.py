import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_login_early.db'
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
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
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


def test_login_empty_credentials_audit(client):
    """Verifica que intentar iniciar sesión con campos vacíos genera un log de auditoría FAILED_LOGIN."""
    from app.models import obtener_todos_logs

    res = client.post('/login', data={'email': '', 'password': ''}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'FAILED_LOGIN'})
    assert len(logs) >= 1
    latest_log = logs[0]
    assert latest_log['status'] == 'FAILED'
    assert latest_log['details'].get('reason') == 'empty_credentials'


def test_login_oversized_credentials_audit(client):
    """Verifica que intentar iniciar sesión con campos que excedan la longitud máxima genera un log FAILED_LOGIN."""
    from app.models import obtener_todos_logs

    long_email = 'a' * 250 + '@example.com'  # > 255 chars
    long_password = 'P' * 130 + '1a'  # > 128 chars
    res = client.post('/login', data={'email': long_email, 'password': long_password}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'FAILED_LOGIN'})
    assert len(logs) >= 1
    matched = [log for log in logs if log['details'].get('reason') == 'credentials_too_long']
    assert len(matched) >= 1
    assert matched[0]['status'] == 'FAILED'
