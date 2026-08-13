import pytest
import sys
import os
from app.extensions import safe_get_remote_address

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_limiter.db'
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

def test_safe_get_remote_address_outside_context():
    """Verifica que la función safe_get_remote_address() retorne '127.0.0.1' o un valor de fallback si se llama fuera de un contexto de request."""
    ip = safe_get_remote_address()
    assert isinstance(ip, str)
    assert ip in {'127.0.0.1', 'unknown'}

def test_safe_get_remote_address_inside_context(client):
    """Verifica que la función safe_get_remote_address() devuelva la IP correcta y saneada dentro de un contexto de solicitud de Flask."""
    with client.application.test_request_context(environ_base={'REMOTE_ADDR': '192.168.1.50'}):
        ip = safe_get_remote_address()
        assert ip == '192.168.1.50'

def test_safe_get_remote_address_malformed_ip(client):
    """Verifica que la función safe_get_remote_address() sanee y valide IPs malformadas dentro de un contexto de Flask."""
    with client.application.test_request_context(environ_base={'REMOTE_ADDR': 'invalid-ip-address'}):
        ip = safe_get_remote_address()
        assert ip == 'unknown'
