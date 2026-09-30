import pytest
import os
import sys
from unittest.mock import patch

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_game_validation.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({"TESTING": True})

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

def test_crear_juego_invalid_inputs(app):
    """Verifica que crear_juego retorne None para inputs inválidos o malformados."""
    from app.models import crear_juego, crear_usuario, ensure_tables
    from werkzeug.security import generate_password_hash

    ensure_tables()
    pw = generate_password_hash("TestPass123!")
    user = crear_usuario("Test", "User", "test_val_game@example.com", "", "", pw)
    assert user is not None
    user_id = user['user_id']

    # Invalid user_id
    assert crear_juego(None, "g1", "Title", "Desc", None) is None
    assert crear_juego("", "g1", "Title", "Desc", None) is None
    assert crear_juego("a" * 37, "g1", "Title", "Desc", None) is None

    # Invalid game_id
    assert crear_juego(user_id, None, "Title", "Desc", None) is None
    assert crear_juego(user_id, "", "Title", "Desc", None) is None
    assert crear_juego(user_id, "g" * 37, "Title", "Desc", None) is None

    # Invalid titulo
    assert crear_juego(user_id, "g1", None, "Desc", None) is None
    assert crear_juego(user_id, "g1", "", "Desc", None) is None
    assert crear_juego(user_id, "g1", "   ", "Desc", None) is None
    assert crear_juego(user_id, "g1", "t" * 256, "Desc", None) is None

def test_crear_juego_database_exception_handled(app):
    """Verifica que crear_juego capture excepciones de DB y retorne None."""
    from app.models import crear_juego, crear_usuario, ensure_tables
    from werkzeug.security import generate_password_hash

    ensure_tables()
    pw = generate_password_hash("TestPass123!")
    user = crear_usuario("Test", "User", "test_val_exc@example.com", "", "", pw)
    assert user is not None
    user_id = user['user_id']

    with patch('app.models.get_session_factory', side_effect=RuntimeError('DB Connection Error')):
        res = crear_juego(user_id, "g123", "Valid Title", "Desc", None)
        assert res is None
