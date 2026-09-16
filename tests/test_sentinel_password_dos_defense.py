import pytest
from unittest.mock import patch
import hashlib
import os

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_password_dos.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models
    import sys
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

def test_profile_password_change_dos_defense(client, app):
    """Verify that changing password with oversized values triggers an instant error and bypasses check_password_hash."""
    from app.models import get_session_factory, User, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    # 1. Create a user
    pw_hash = generate_password_hash("Secure123!")
    user = crear_usuario(
        nombre="Test User",
        apellido="",
        email="test_dos_profile@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw_hash
    )
    assert user is not None

    # 2. Log in
    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Post profile password change with oversized password
    with patch('app.routes.check_password_hash') as mock_check:
        response = client.post('/perfil', data={
            'form_name': 'password',
            'current_password': 'Secure123!',
            'password': 'A' * 129,
            'confirm_password': 'A' * 129
        }, follow_redirects=True)

        assert response.status_code == 200
        mock_check.assert_not_called()

def test_reset_password_dos_defense(client, app):
    """Verify that resetting password with oversized values triggers an instant error and bypasses check_password_hash."""
    from app.models import get_session_factory, User, crear_usuario, crear_reset_token
    from werkzeug.security import generate_password_hash
    import hashlib

    # 1. Create a user
    pw_hash = generate_password_hash("Secure123!")
    user = crear_usuario(
        nombre="Test User Reset",
        apellido="",
        email="test_dos_reset@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw_hash
    )
    assert user is not None

    # 2. Generate a reset token
    token_res = crear_reset_token(user['user_id'], '127.0.0.1')
    assert token_res['success'] is True
    token = token_res['token']

    # 3. Post to reset-password with oversized password
    with patch('app.routes.check_password_hash') as mock_check:
        response = client.post(f'/reset-password/{token}', data={
            'password': 'B' * 129,
            'confirm_password': 'B' * 129
        }, follow_redirects=True)

        assert response.status_code == 200
        mock_check.assert_not_called()
