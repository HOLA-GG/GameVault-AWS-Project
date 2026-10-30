import os
import sys
from pathlib import Path
from unittest.mock import patch
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_landing_exc.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

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
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_landing_handles_backend_exception_gracefully(client):
    """Verifica que / maneje excepciones al consultar colecciones sin arrojar HTTP 500."""
    with patch('app.routes.obtener_colecciones_publicas', side_effect=Exception("Database connection error")):
        response = client.get('/')
        assert response.status_code == 200
        assert b"GameVault" in response.data

def test_landing_handles_sample_cache_exception_gracefully(client):
    """Verifica que / maneje excepciones en el caché de muestra sin arrojar HTTP 500."""
    with patch('app.routes.obtener_sample_collections_cached', side_effect=Exception("Cache lock error")):
        response = client.get('/')
        assert response.status_code == 200
        assert b"GameVault" in response.data
