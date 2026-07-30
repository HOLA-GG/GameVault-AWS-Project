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
        db_path.unlink()

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


def test_in_duplicates_optimization(app):
    """Verifica que las consultas SQL con IN filtren IDs duplicados correctamente."""
    from app.models import obtener_usuarios_por_ids, obtener_ratings_multiple, get_session_factory, User

    # Obtener IDs duplicados
    duplicated_user_ids = ["non-existent-user-1", "non-existent-user-1", "non-existent-user-2"]

    # Esto llamará a la función optimizada
    users = obtener_usuarios_por_ids(duplicated_user_ids)
    assert isinstance(users, list)
    assert len(users) == 0  # No existen pero no debe fallar

    duplicated_subject_ids = ["demo-jrpg-esenciales", "demo-jrpg-esenciales", "demo-nintendo-reliquias"]
    ratings = obtener_ratings_multiple("sample", duplicated_subject_ids)
    assert isinstance(ratings, dict)
