"""Test suite verifying cover image cleanup when deleting a user account."""

from unittest.mock import patch
import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'test_user_del_cleanup.db'
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
        "STORAGE_BACKEND": "local",
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass


def test_eliminar_usuario_cleans_up_game_images(app):
    """Verify that deleting a user invokes image cleanup for all associated user games."""
    from app.models import (
        crear_usuario,
        crear_juego,
        eliminar_usuario,
        obtener_usuario_por_id,
        obtener_juegos_por_usuario,
    )

    with app.app_context():
        # Create test user
        user = crear_usuario("UserToDelete", "Test", "delete_me@example.com", "+1", "5551234567", "scrypt:hash")
        assert user is not None
        user_id = user['user_id']

        # Create two games for this user, one with an image_url and one without
        game1 = crear_juego(user_id, "g-del-1", "Game 1", "Desc 1", "/static/uploads/covers/test1.jpg")
        game2 = crear_juego(user_id, "g-del-2", "Game 2", "Desc 2", None)

        assert game1 is not None
        assert game2 is not None

        # Call eliminar_usuario while mocking eliminar_imagen_s3 to verify it's triggered
        with patch('app.models.eliminar_imagen_s3') as mock_eliminar_s3:
            mock_eliminar_s3.return_value = True
            res = eliminar_usuario(user_id)

            assert res['success'] is True
            mock_eliminar_s3.assert_called_once_with("/static/uploads/covers/test1.jpg")

        # Confirm user and games are removed from DB
        assert obtener_usuario_por_id(user_id) is None
        assert obtener_juegos_por_usuario(user_id) == []
