import pytest
import sys
import os
import uuid
from app.models import parse_date_filter, limpiar_logs_antiguos

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_dos_hardening.db'
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

    # Cleanup after all tests in this file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_current_password_length_limit(client):
    """Verify that current_password longer than 128 characters is rejected on change password."""
    # Register and automatically log in
    response = client.post('/registro', data={
        'nombre': 'Test User',
        'email': 'profile_dos@example.com',
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    assert response.status_code == 302

    # Attempt password change with an extremely long current password
    long_pwd = "A" * 150
    response = client.post('/perfil', data={
        'form_name': 'password',
        'current_password': long_pwd,
        'password': 'NewSecurePass123!',
        'confirm_password': 'NewSecurePass123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'La contrase\xc3\xb1a actual es demasiado larga' in response.data

def test_token_length_limit_verify(client):
    """Verify that a token longer than 128 characters is rejected on verify_token without crash."""
    long_token = "A" * 150
    response = client.post('/verify-token', data={
        'token': long_token
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'El token no es v\xc3\xa1lido.' in response.data

def test_token_length_limit_reset(client):
    """Verify that a token longer than 128 characters is rejected on reset_password_with_email without crash."""
    long_token = "A" * 150
    response = client.get(f'/reset-password/{long_token}', follow_redirects=True)

    assert response.status_code == 200
    assert b'El token no es v\xc3\xa1lido.' in response.data

def test_date_overflow_handling(app):
    """Verify parse_date_filter and limpiar_logs_antiguos handle date/time overflows gracefully."""
    with app.app_context():
        # parse_date_filter overflow with datetime.max close
        assert parse_date_filter("9999-12-31T23:59:59.999999", end=True) is None

        # parse_date_filter invalid input handles gracefully
        assert parse_date_filter("invalid-date") is None

        # limpiar_logs_antiguos handling extremely large days gracefully
        res = limpiar_logs_antiguos(days=10**18)
        assert res['error'] is None
        assert 'deleted' in res
