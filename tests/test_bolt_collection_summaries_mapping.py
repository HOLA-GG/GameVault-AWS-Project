"""Tests for Bolt optimization in obtener_resumenes_colecciones mapping logic."""

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


def test_obtener_resumenes_colecciones_mapping_optimization(app):
    """Verifies that obtener_resumenes_colecciones maps row mappings correctly and accurately."""
    with app.app_context():
        from app.models import (
            crear_juego,
            crear_usuario,
            init_database,
            obtener_resumenes_colecciones,
        )

        init_database()
        user1 = crear_usuario('Collector Alpha', 'One', 'collector1@example.com', '+1', '5551111111', 'scrypt:32768:8:1$hash123')
        user2 = crear_usuario('Collector Beta', 'Two', 'collector2@example.com', '+1', '5552222222', 'scrypt:32768:8:1$hash456')

        assert user1 is not None
        assert user2 is not None

        crear_juego(user1['user_id'], 'g1', 'Zelda: Ocarina of Time', 'Masterpiece JRPG/Adventure', '', 'Nintendo', 'Bueno', 'Biblioteca', 'Alta', 10, True)
        crear_juego(user1['user_id'], 'g2', 'Super Mario 64', 'Platformer', '', 'Nintendo', 'Bueno', 'Biblioteca', 'Alta', 9, False)

        crear_juego(user2['user_id'], 'g3', 'Halo: CE', 'Sci-fi FPS', '', 'Xbox', 'Bueno', 'Biblioteca', 'Media', 8, False)

        summaries = obtener_resumenes_colecciones()

        assert len(summaries) >= 2

        alpha_summary = next((s for s in summaries if s['user_id'] == user1['user_id']), None)
        assert alpha_summary is not None
        assert alpha_summary['owner_name'] == 'Collector Alpha'
        assert alpha_summary['total_games'] == 2
        assert alpha_summary['favorites_count'] == 1
        assert alpha_summary['average_rating'] == 9.5
        assert alpha_summary['dominant_platform'] == 'Nintendo'

        beta_summary = next((s for s in summaries if s['user_id'] == user2['user_id']), None)
        assert beta_summary is not None
        assert beta_summary['owner_name'] == 'Collector Beta'
        assert beta_summary['total_games'] == 1
        assert beta_summary['favorites_count'] == 0
        assert beta_summary['average_rating'] == 8.0
        assert beta_summary['dominant_platform'] == 'Xbox'
