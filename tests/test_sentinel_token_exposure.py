import pytest
import sys
import os
from unittest.mock import patch

@pytest.fixture
def app_prod(monkeypatch):
    db_file = 'gamevault_test_exposure.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'production')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')

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
        "SHOW_RESET_DEBUG_TOKEN": False,
        "MAIL_SUPPRESS_SEND": True # This makes email_sent=False in the route
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
def client_prod(app_prod):
    return app_prod.test_client()

def test_forgot_password_no_token_exposure_in_production(client_prod):
    """
    Vulnerability: forgot_password route exposes token in production if email fails.
    This test verifies that the token is NOT exposed when APP_ENV is production and SHOW_RESET_DEBUG_TOKEN is False.
    """
    from app.models import crear_usuario
    email = "exposure_test@example.com"
    crear_usuario("Exposure", "Test", email, "", "", "hash_password")

    # We mock sending email to fail (returning False)
    with patch('app.routes.enviar_email_reset_password', return_value=False):
        response = client_prod.post('/forgot-password', data={'email': email}, follow_redirects=True)

    assert response.status_code == 200
    html = response.data.decode('utf-8')
    # Should NOT see the debug token
    assert "Recuperación asistida" not in html
    assert "Token:" not in html

def test_forgot_password_manual_no_token_exposure_in_production(client_prod):
    """
    Vulnerability: forgot_password_manual route ALWAYS exposes token on success.
    This test verifies that the token is NOT exposed in production-like settings.
    """
    from app.models import crear_usuario
    email = "manual_exposure@example.com"
    telefono = "123456789"
    crear_usuario("Manual", "Exposure", email, "", telefono, "hash_password")

    response = client_prod.post('/forgot-password/manual', data={
        'email': email,
        'telefono': telefono
    })

    # The current implementation ALWAYS shows the token, so this test should FAIL before the fix.
    assert response.status_code == 200 or response.status_code == 302
    html = response.data.decode('utf-8')

    # In production, we should NOT see the token
    assert "Recuperación asistida" not in html
    assert "Token:" not in html
