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


def test_obtener_metricas_coleccion_shortcircuits_when_no_high_priority(app):
    """Verifica que obtener_metricas_coleccion devuelva next_focus=None sin errores cuando high_priority_count es 0."""
    from app.models import (
        crear_usuario,
        crear_juego,
        obtener_metricas_coleccion,
        init_database,
    )

    init_database()
    user = crear_usuario(
        'ShortCircuitUser',
        'Test',
        'shortcircuit_test@example.com',
        '',
        '',
        'scrypt:32768:8:1$mockhash',
    )
    assert user is not None
    user_id = user['user_id']

    # Crear juegos sin prioridad 'Alta'
    g1 = crear_juego(user_id, 'game-sc-1', 'Juego Media 1', 'Desc 1', '', prioridad='Media')
    g2 = crear_juego(user_id, 'game-sc-2', 'Juego Baja 1', 'Desc 2', '', prioridad='Baja')
    assert g1 is not None
    assert g2 is not None

    metrics = obtener_metricas_coleccion(user_id, full=True)
    assert metrics['total_games'] == 2
    assert metrics['high_priority_count'] == 0
    assert metrics['next_focus'] is None


def test_obtener_metricas_coleccion_returns_next_focus_when_high_priority_exists(app):
    """Verifica que obtener_metricas_coleccion obtenga el juego next_focus correcto cuando existe prioridad Alta."""
    from app.models import (
        crear_usuario,
        crear_juego,
        obtener_metricas_coleccion,
        init_database,
    )

    init_database()
    user = crear_usuario(
        'HighPriUser',
        'Test',
        'highpri_test@example.com',
        '',
        '',
        'scrypt:32768:8:1$mockhash',
    )
    assert user is not None
    user_id = user['user_id']

    # Crear juego con prioridad 'Alta' y categoría no Completado
    g_high = crear_juego(
        user_id,
        'game-high-1',
        'Juego Alta Prioridad',
        'Desc High',
        '',
        prioridad='Alta',
        categoria='Backlog',
    )
    assert g_high is not None

    metrics = obtener_metricas_coleccion(user_id, full=True)
    assert metrics['total_games'] == 1
    assert metrics['high_priority_count'] == 1
    assert metrics['next_focus'] is not None
    assert metrics['next_focus']['game_id'] == 'game-high-1'
    assert metrics['next_focus']['titulo'] == 'Juego Alta Prioridad'
