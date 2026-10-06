import os
import sys
import pytest
from app import create_app


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_token_exception.db'
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


@pytest.fixture
def client(app):
    return app.test_client()


def test_crear_reset_token_db_exception(app, monkeypatch):
    """Verifies crear_reset_token catches DB exceptions and returns a failure dict instead of crashing."""
    import app.models

    user = app.models.crear_usuario(
        nombre="Reset Test",
        apellido="",
        email="reset_exception@example.com",
        prefijo_pais="",
        telefono="",
        password_hash="Hash1234!",
    )
    assert user is not None

    def mock_get_session_factory():
        class MockSession:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            def add(self, item):
                pass
            def commit(self):
                raise RuntimeError("Database connection lost")
        return MockSession

    monkeypatch.setattr(app.models, "get_session_factory", mock_get_session_factory)

    result = app.models.crear_reset_token(user["user_id"], "127.0.0.1")
    assert result["success"] is False
    assert result["token"] is None
    assert result["expires_at"] is None
    assert result["error"] == "Error al generar token de recuperación"


def test_forgot_password_audit_log_on_token_creation_failure(app, client, monkeypatch):
    """Verifies forgot_password route logs a FAILED audit entry when crear_reset_token fails."""
    import app.models
    from sqlalchemy import select

    user = app.models.crear_usuario(
        nombre="Reset Audit Test",
        apellido="",
        email="reset_audit@example.com",
        prefijo_pais="",
        telefono="",
        password_hash="Hash1234!",
    )
    assert user is not None

    monkeypatch.setattr(
        "app.routes.crear_reset_token",
        lambda user_id, ip: {"success": False, "token": None, "expires_at": None, "error": "db_error"}
    )

    response = client.post("/forgot-password", data={"email": "reset_audit@example.com"}, follow_redirects=True)
    assert response.status_code == 200

    session_factory = app.models.get_session_factory()
    with session_factory() as db_session:
        logs = db_session.scalars(
            select(app.models.AuditLog).where(
                app.models.AuditLog.user_id == user["user_id"],
                app.models.AuditLog.action == "PASSWORD_RESET_REQUEST"
            )
        ).all()

        assert len(logs) == 1
        assert logs[0].status == "FAILED"
        assert logs[0].details.get("reason") == "token_creation_failed"
