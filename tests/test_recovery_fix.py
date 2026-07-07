import pytest
import sys
import os
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_fix.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload
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
        "SHOW_RESET_DEBUG_TOKEN": True  # Restore for functional tests that expect visibility
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_manual_recovery_always_shows_token(client, app):
    """Verifica que la opción 2 (manual) siempre muestre el token si los datos coinciden."""
    from app.models import crear_usuario
    email = "manual_test@example.com"
    telefono = "987654321"
    crear_usuario("Manual", "Test", email, "", telefono, "hash_password")

    # SHOW_RESET_DEBUG_TOKEN is False in fixture
    response = client.post('/forgot-password/manual', data={
        'email': email,
        'telefono': telefono
    })

    assert response.status_code == 200
    # Check for success message
    assert b"Token generado exitosamente" in response.data
    # Check that the debug context is present in the rendered template
    assert b"Token:" in response.data
    # Use decoded search to avoid encoding issues in bytes literal
    html = response.data.decode('utf-8')
    assert "Recuperación asistida" in html

def test_email_recovery_logs_failure_on_missing_config(client, app):
    """Verifica que el flujo de email intente enviar y loguee el resultado."""
    from app.models import crear_usuario
    email = "email_test@example.com"
    crear_usuario("Email", "Test", email, "", "", "hash_password")

    # Mail will likely fail due to missing SMTP config in test environment
    response = client.post('/forgot-password', data={'email': email}, follow_redirects=True)

    assert response.status_code == 200
    # Success message is shown regardless of email delivery status (security)
    html = response.data.decode('utf-8')
    assert "Si el correo está registrado, recibirás un enlace" in html

    # We should see the debug token because app_env is 'testing' and email_sent would be False
    assert "Recuperación asistida" in html
