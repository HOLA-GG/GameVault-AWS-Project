import pytest
import sys
import os
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_demo_exc.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
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
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_demo_post_exception_handling(client):
    """Verifica que excepciones inesperadas durante POST /demo sean capturadas, logueadas y redirigidas con mensaje seguro."""
    with patch('app.routes.procesar_imagen_base64', side_effect=RuntimeError("Unexpected processing crash")):
        import io
        data = {
            'titulo': 'Test Game',
            'imagen': (io.BytesIO(b'fake_image_data'), 'test.jpg')
        }
        response = client.post('/demo', data=data, content_type='multipart/form-data')

        # Debería capturar el error y redirigir con 302 a /demo en vez de crash 500
        assert response.status_code == 302
        assert response.headers['Location'].endswith('/demo')

        with client.session_transaction() as sess:
            flashes = sess.get('_flashes', [])
            assert any("Ocurrió un error inesperado al procesar la demo." in msg[1] for msg in flashes)
