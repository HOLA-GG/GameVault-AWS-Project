import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_pw_reset_early.db'
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


def test_forgot_password_empty_email_audit(client):
    """Verifica que solicitar reset con email vacío registra log FAILED de PASSWORD_RESET_REQUEST."""
    from app.models import obtener_todos_logs

    res = client.post('/forgot-password', data={'email': ''}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'PASSWORD_RESET_REQUEST'})
    assert len(logs) >= 1
    matched = [l for l in logs if l['details'].get('reason') == 'empty_email']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'


def test_forgot_password_oversized_email_audit(client):
    """Verifica que solicitar reset con email que supere 255 caracteres registra log FAILED."""
    from app.models import obtener_todos_logs

    long_email = 'a' * 250 + '@example.com'
    res = client.post('/forgot-password', data={'email': long_email}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'PASSWORD_RESET_REQUEST'})
    matched = [l for l in logs if l['details'].get('reason') == 'email_too_long']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'


def test_forgot_password_manual_empty_credentials_audit(client):
    """Verifica que recuperar manualmente con campos vacíos registra log FAILED."""
    from app.models import obtener_todos_logs

    res = client.post('/forgot-password/manual', data={'email': '', 'telefono': ''}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'PASSWORD_RESET_REQUEST'})
    matched = [l for l in logs if l['details'].get('reason') == 'empty_credentials' and l['details'].get('channel') == 'manual_token']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'


def test_forgot_password_manual_oversized_credentials_audit(client):
    """Verifica que recuperar manualmente con campos excesivamente largos registra log FAILED."""
    from app.models import obtener_todos_logs

    long_email = 'b' * 250 + '@example.com'
    long_phone = '1' * 25
    res = client.post('/forgot-password/manual', data={'email': long_email, 'telefono': long_phone}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'PASSWORD_RESET_REQUEST'})
    matched = [l for l in logs if l['details'].get('reason') == 'credentials_too_long' and l['details'].get('channel') == 'manual_token']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'
