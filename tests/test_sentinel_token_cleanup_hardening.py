import os
import sys
import pytest
from datetime import datetime, timedelta, timezone

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_token_cleanup.db'
    if os.path.exists(db_file):
        os.remove(db_file)

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
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass


def test_eliminar_tokens_expirados_success(app):
    """Verifica que los tokens expirados se eliminen correctamente mientras se conservan los activos."""
    from app.models import (
        get_session_factory,
        crear_usuario,
        crear_reset_token,
        eliminar_tokens_expirados,
        PasswordResetToken,
        utcnow,
    )
    from sqlalchemy import select

    user = crear_usuario(
        nombre="Cleanup User",
        apellido="",
        email="cleanup@example.com",
        prefijo_pais="",
        telefono="",
        password_hash="hash123",
    )
    user_id = user['user_id']

    # Crear token normal
    res1 = crear_reset_token(user_id)
    token1 = res1['token']

    # Crear token expirado forzando expires_at en DB
    res2 = crear_reset_token(user_id)
    token2 = res2['token']

    session_factory = get_session_factory()
    with session_factory() as session:
        expired_token_obj = session.scalar(
            select(PasswordResetToken).where(PasswordResetToken.user_id == user_id).order_by(PasswordResetToken.created_at.desc())
        )
        expired_token_obj.expires_at = utcnow() - timedelta(minutes=10)
        session.commit()

    # Ejecutar limpieza
    res = eliminar_tokens_expirados()
    assert res['error'] is None
    assert res['deleted'] == 1

    with session_factory() as session:
        tokens = session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user_id)).all()
        assert len(tokens) == 1


def test_eliminar_tokens_expirados_error_handling(app, monkeypatch):
    """Verifica que si la eliminación de tokens falla por error de base de datos, se retorne un diccionario con el error sin lanzar excepción."""
    import app.models

    def mock_get_session_factory():
        class MockSession:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            def execute(self, stmt):
                raise Exception("database execution error")
        return MockSession

    monkeypatch.setattr(app.models, 'get_session_factory', mock_get_session_factory)

    res = app.models.eliminar_tokens_expirados()
    assert res['deleted'] == 0
    assert 'database execution error' in res['error']
