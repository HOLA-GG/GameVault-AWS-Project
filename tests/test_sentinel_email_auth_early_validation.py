import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_email_auth_early_val.db'
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


def test_login_invalid_email_format_audit(client):
    """Verifica que un intento de login con formato de email inválido o puntos consecutivos registra log FAILED."""
    from app.models import obtener_todos_logs

    res = client.post('/login', data={'email': 'user..name@example.com', 'password': 'Password123'}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'FAILED_LOGIN'})
    matched = [l for l in logs if l['details'].get('reason') == 'invalid_email_format']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'
    assert matched[0]['details']['email'] == 'user..name@example.com'


def test_forgot_password_invalid_email_format_audit(client):
    """Verifica que solicitar recuperación de contraseña con formato de email inválido registra log FAILED."""
    from app.models import obtener_todos_logs

    res = client.post('/forgot-password', data={'email': 'invalid_email_str'}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'PASSWORD_RESET_REQUEST'})
    matched = [l for l in logs if l['details'].get('reason') == 'invalid_email_format']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'


def test_forgot_password_manual_invalid_credentials_format_audit(client):
    """Verifica que recuperar manualmente con email o teléfono de formato inválido registra log FAILED."""
    from app.models import obtener_todos_logs

    # Invalid phone (contains non-digits)
    res = client.post('/forgot-password/manual', data={'email': 'user@example.com', 'telefono': 'abc-1234'}, follow_redirects=True)
    assert res.status_code == 200

    logs = obtener_todos_logs({'action': 'PASSWORD_RESET_REQUEST'})
    matched = [l for l in logs if l['details'].get('reason') == 'invalid_credentials_format' and l['details'].get('channel') == 'manual_token']
    assert len(matched) == 1
    assert matched[0]['status'] == 'FAILED'
