"""Tests de robustez para funciones de tokens de recuperación contra tipos inválidos y nulos."""

import pytest
from app.models import hash_token, obtener_token_por_valor, validar_reset_token, usar_token


def test_hash_token_robustness():
    """Verifica que hash_token maneja None, cadenas vacías y tipos no-cadena sin fallar."""
    # None input
    assert isinstance(hash_token(None), str)
    assert len(hash_token(None)) == 64

    # Empty string input
    assert hash_token("") == hash_token(None)

    # Integer input
    assert isinstance(hash_token(12345), str)


def test_obtener_token_por_valor_robustness():
    """Verifica que obtener_token_por_valor retorna lista vacía para inputs inválidos."""
    assert obtener_token_por_valor(None) == []
    assert obtener_token_por_valor("") == []
    assert obtener_token_por_valor(12345) == []
    assert obtener_token_por_valor({"token": "abc"}) == []
    assert obtener_token_por_valor(["token_a"]) == []


def test_validar_reset_token_robustness():
    """Verifica que validar_reset_token responde con diccionario de error para inputs inválidos."""
    for invalid_token in (None, "", 12345, {"token": "xyz"}, ["abc"]):
        res = validar_reset_token(invalid_token)
        assert res["valid"] is False
        assert res["user_id"] is None
        assert "error" in res


def test_usar_token_robustness():
    """Verifica que usar_token responde con diccionario de error para inputs inválidos."""
    for invalid_token in (None, "", 12345, {"token": "xyz"}, ["abc"]):
        res = usar_token(invalid_token)
        assert res["success"] is False
        assert "error" in res


@pytest.fixture
def app(monkeypatch):
    import os, sys
    db_file = 'gamevault_test_token_robustness.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

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


def test_verify_token_inactive_or_missing_user(client, app):
    """Verifica que verify_token rechace tokens asociados a usuarios inactivos o inexistentes."""
    import uuid
    from sqlalchemy import select
    from app.models import get_session_factory, User, AuditLog, crear_reset_token

    unique_email = f"verify_inactive_{uuid.uuid4()}@example.com"
    initial_password = "SecurePass123!"

    # 1. Register user
    client.post('/registro', data={
        'nombre': 'Inactive User',
        'email': unique_email,
        'password': initial_password,
        'confirm_password': initial_password
    })
    client.post('/logout')

    # 2. Get user_id & mark user as inactive
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == unique_email))
        user_id = user.user_id
        user.status = 'inactive'
        session.commit()

    # 3. Create reset token
    token_res = crear_reset_token(user_id, "127.0.0.1")
    assert token_res['success']
    token = token_res['token']

    # 4. Post to /verify-token
    response = client.post('/verify-token', data={'token': token}, follow_redirects=True)

    # 5. Assert flash message and redirect to validate-token
    assert response.status_code == 200
    assert b'No se pudo procesar la solicitud para esta cuenta.' in response.data

    # 6. Assert audit log contains TOKEN_VALIDATION_FAILED
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user_id,
                AuditLog.action == 'TOKEN_VALIDATION_FAILED',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'user_not_found_or_inactive'
        assert log.details.get('context') == 'verify_token'


def test_verify_token_empty_and_oversized_audit_logs(client, app):
    """Verifica que verify_token y reset_password_with_email registren logs de auditoría ante tokens vacíos o sobrepasados."""
    from sqlalchemy import select
    from app.models import get_session_factory, AuditLog

    session_factory = get_session_factory()

    # 1. Post empty token to /verify-token
    response = client.post('/verify-token', data={'token': ''}, follow_redirects=True)
    assert response.status_code == 200

    with session_factory() as session:
        log_empty = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == 'TOKEN_VALIDATION_FAILED', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log_empty is not None
        assert log_empty.details.get('reason') == 'empty_token'
        assert log_empty.details.get('context') == 'verify_token'

    # 2. Post oversized token (150 chars) to /verify-token
    oversized_token = "a" * 150
    response_over = client.post('/verify-token', data={'token': oversized_token}, follow_redirects=True)
    assert response_over.status_code == 200

    with session_factory() as session:
        log_over = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == 'TOKEN_VALIDATION_FAILED', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log_over is not None
        assert log_over.details.get('reason') == 'token_too_long'
        assert log_over.details.get('context') == 'verify_token'

    # 3. GET oversized token route /reset-password/<token>
    response_reset = client.get(f'/reset-password/{oversized_token}', follow_redirects=True)
    assert response_reset.status_code == 200

    with session_factory() as session:
        log_reset_over = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == 'TOKEN_VALIDATION_FAILED', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log_reset_over is not None
        assert log_reset_over.details.get('reason') == 'token_too_long'
        assert log_reset_over.details.get('context') == 'reset_password'
