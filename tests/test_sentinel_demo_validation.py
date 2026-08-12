import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_demo_val.db'
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

def test_demo_title_length_limit(client):
    """Verifica que el endpoint de demo limite la longitud del título para evitar DoS por memoria."""
    # Enviar un título extremadamente largo (> 255 caracteres)
    giant_title = "A" * 300
    response = client.post('/demo', data={
        'titulo': giant_title
    })

    # Debería redirigir de vuelta a la página de la demo
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/demo')

    # Verificar que el mensaje de error fue flasheado
    with client.session_transaction() as sess:
        # Flask flash messages are stored under '_flashes' in session
        flashes = sess.get('_flashes', [])
        assert any("El título es demasiado largo" in msg[1] for msg in flashes)

def test_demo_title_valid_length(client):
    """Verifica que un título con longitud válida sea aceptado en el endpoint de demo."""
    # Para simular que procese la imagen (o que falle porque no hay imagen),
    # enviamos un título válido pero sin imagen o con imagen vacía.
    # En este caso, si no enviamos una imagen válida, is_valid_image_file retornará False
    # (por "Debes seleccionar una imagen") y se flasheará ese error de validación de imagen,
    # lo cual significa que el título superó la validación de longitud correctamente.
    valid_title = "Mi juego favorito"
    response = client.post('/demo', data={
        'titulo': valid_title
    })

    assert response.status_code == 302
    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        # Debería haber flasheado el error de imagen, no el de título largo
        assert not any("El título es demasiado largo" in msg[1] for msg in flashes)
        assert any("Debes seleccionar una imagen" in msg[1] for msg in flashes)
