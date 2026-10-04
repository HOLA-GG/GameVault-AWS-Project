import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_game_id_hardening.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

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


def test_eliminar_juego_invalid_inputs(app):
    """Verifica que eliminar_juego maneje entradas nulas, vacías o de longitud excesiva de forma defensiva."""
    from app.models import eliminar_juego

    with app.app_context():
        # user_id / game_id inválidos (None, no-string, vacíos, demasiado largos)
        assert eliminar_juego(None, 'game-123') == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert eliminar_juego('', 'game-123') == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert eliminar_juego('a' * 37, 'game-123') == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert eliminar_juego(12345, 'game-123') == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}

        assert eliminar_juego('user-123', None) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert eliminar_juego('user-123', '') == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert eliminar_juego('user-123', 'b' * 37) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert eliminar_juego('user-123', ['invalid']) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}


def test_actualizar_juego_invalid_inputs(app):
    """Verifica que actualizar_juego maneje entradas nulas, vacías, de longitud excesiva o de tipo inválido."""
    from app.models import actualizar_juego

    with app.app_context():
        # user_id / game_id inválidos
        assert actualizar_juego(None, 'game-123', {'titulo': 'New Title'}) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert actualizar_juego('', 'game-123', {'titulo': 'New Title'}) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert actualizar_juego('a' * 37, 'game-123', {'titulo': 'New Title'}) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}

        assert actualizar_juego('user-123', None, {'titulo': 'New Title'}) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        assert actualizar_juego('user-123', 'b' * 37, {'titulo': 'New Title'}) == {'success': False, 'juego': None, 'error': 'Juego no encontrado'}

        # nuevos_datos no es un diccionario
        assert actualizar_juego('user-123', 'game-123', None) == {'success': False, 'juego': None, 'error': 'Datos de juego inválidos'}
        assert actualizar_juego('user-123', 'game-123', 'not-a-dict') == {'success': False, 'juego': None, 'error': 'Datos de juego inválidos'}
