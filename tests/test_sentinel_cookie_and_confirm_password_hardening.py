import pytest
import sys
import os
import hashlib
from app.models import get_session_factory, User, crear_usuario, generate_password_hash

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_cookie_confirm.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models
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
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_confirm_password_length_limit_registro(client):
    """Verify registration rejects extremely long confirm_password."""
    response = client.post('/registro', data={
        'nombre': 'Test Registration',
        'email': 'reg_test@example.com',
        'password': 'SecurePass123!',
        'confirm_password': 'A' * 150
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'La confirmaci\xc3\xb3n de la contrase\xc3\xb1a es demasiado larga' in response.data

def test_confirm_password_length_limit_profile(client):
    """Verify profile password update rejects extremely long confirm_password."""
    # Register and automatically log in
    client.post('/registro', data={
        'nombre': 'Test Profile',
        'email': 'profile_test@example.com',
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })

    response = client.post('/perfil', data={
        'form_name': 'password',
        'current_password': 'SecurePass123!',
        'password': 'NewSecurePass123!',
        'confirm_password': 'A' * 150
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'La confirmaci\xc3\xb3n de la contrase\xc3\xb1a es demasiado larga' in response.data

def test_confirm_password_length_limit_reset_password(client, app):
    """Verify password reset via token rejects extremely long confirm_password."""
    from app.models import crear_reset_token
    # Register
    client.post('/registro', data={
        'nombre': 'Test Reset',
        'email': 'reset_test@example.com',
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    client.post('/logout')

    # Create a dummy token for this user
    with app.app_context():
        from app.models import obtener_usuario_por_email
        user = obtener_usuario_por_email('reset_test@example.com', format_dates=False)
        result = crear_reset_token(user['user_id'], '127.0.0.1')
        token = result['token']

    # Try to reset with very long confirm_password
    response = client.post(f'/reset-password/{token}', data={
        'password': 'NewSecurePass123!',
        'confirm_password': 'A' * 150
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'La confirmaci\xc3\xb3n de la contrase\xc3\xb1a es demasiado larga' in response.data

def test_session_cookie_name_not_secure(app):
    """Verify cookie name defaults to 'session' when secure is False."""
    assert app.config['SESSION_COOKIE_SECURE'] is False
    assert app.config['SESSION_COOKIE_NAME'] == 'session'

def test_session_cookie_name_secure(monkeypatch):
    """Verify cookie name is set to '__Host-session' when secure is True."""
    monkeypatch.setenv('SESSION_COOKIE_SECURE', 'true')
    # Reload app to parse the env var
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    assert flask_app.config['SESSION_COOKIE_SECURE'] is True
    assert flask_app.config['SESSION_COOKIE_NAME'] == '__Host-session'
