from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_path = PROJECT_ROOT / 'gamevault_test.db'
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    env = {
        'APP_ENV': 'testing',
        'SECRET_KEY': 'test-secret-key',
        'AWS_REGION': 'us-east-1',
        'DATABASE_URL': 'sqlite+pysqlite:///gamevault_test.db',
        'S3_BUCKET_NAME': 'gamevault-test-bucket',
        'DYNAMODB_TABLE': 'GameVaultTest',
        'DYNAMODB_USERS_TABLE': 'GameVaultUsersTest',
        'DYNAMODB_RESET_TABLE': 'GameVaultPasswordResetTest',
        'DYNAMODB_AUDIT_TABLE': 'GameVaultAuditLogsTest',
        'STORAGE_BACKEND': 'none',
        'MAIL_SUPPRESS_SEND': 'true',
        'WTF_CSRF_ENABLED': 'false',
        'SESSION_COOKIE_SECURE': 'false',
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    app_module = importlib.import_module('app')
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, MAIL_SUPPRESS_SEND=True)
    return flask_app


def test_obtener_metricas_filter_options_consolidation(app):
    """Verify that obtener_metricas_coleccion correctly aggregates and sorts filter options in-memory."""
    from app.models import (
        crear_usuario,
        crear_juego,
        obtener_metricas_coleccion,
        get_session_factory,
    )

    # 1. Create a test user
    user = crear_usuario(
        nombre="Test Bolt",
        apellido="Metricas",
        email="bolt_metricas@test.com",
        prefijo_pais="+34",
        telefono="123456789",
        password_hash="scrypt:32768:8:1$mockhash",
    )
    assert user is not None
    user_id = user['user_id']

    # 2. Add some test games with specific platforms, states, and categories
    # Mix of uppercase/lowercase and order to test sorting
    crear_juego(
        user_id=user_id,
        game_id="game-1",
        titulo="Zelda: Breath of the Wild",
        descripcion="Adventure",
        imagen_url=None,
        plataforma="Nintendo Switch",
        estado="Nuevo",
        categoria="Jugando",
    )
    crear_juego(
        user_id=user_id,
        game_id="game-2",
        titulo="Halo Infinite",
        descripcion="FPS",
        imagen_url=None,
        plataforma="Xbox Series X",
        estado="Bueno",
        categoria="Backlog",
    )
    crear_juego(
        user_id=user_id,
        game_id="game-3",
        titulo="Elden Ring",
        descripcion="Action RPG",
        imagen_url=None,
        plataforma="PC",
        estado="Como Nuevo",
        categoria="Biblioteca",
    )
    # Add one default platform / condition to ensure they are excluded from filter options
    crear_juego(
        user_id=user_id,
        game_id="game-4",
        titulo="Default Game",
        descripcion="Default",
        imagen_url=None,
        plataforma="Sin plataforma",  # Should be excluded
        estado="N/A",  # Should be excluded
        categoria="Wishlist",  # Should be included
    )

    # 3. Call the consolidated function
    metrics = obtener_metricas_coleccion(user_id, full=True)

    # 4. Verify correct metrics calculations
    assert metrics['total_games'] == 4
    assert metrics['platforms_count'] == 4  # Includes 'Sin plataforma' in general distinct platform count

    # 5. Verify the filter_options are correctly parsed, filtered, and sorted in-memory
    filter_opts = metrics['filter_options']

    # Platforms should be sorted: ['Nintendo Switch', 'PC', 'Xbox Series X']
    # 'Sin plataforma' must be excluded.
    assert filter_opts['plataformas'] == ['Nintendo Switch', 'PC', 'Xbox Series X']

    # States should be sorted: ['Bueno', 'Como Nuevo', 'Nuevo']
    # 'N/A' must be excluded.
    assert filter_opts['estados'] == ['Bueno', 'Como Nuevo', 'Nuevo']

    # Categories should be sorted: ['Backlog', 'Biblioteca', 'Jugando', 'Wishlist']
    assert filter_opts['categorias'] == ['Backlog', 'Biblioteca', 'Jugando', 'Wishlist']
