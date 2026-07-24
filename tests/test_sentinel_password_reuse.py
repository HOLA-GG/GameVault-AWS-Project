import pytest
import uuid
import sys
import os
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_reuse.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models to guarantee database url is set
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

def test_password_change_rejects_reuse(client, app):
    """Verifica que el cambio de contraseña rechace usar la misma contraseña actual."""
    from app.models import get_session_factory, User, AuditLog
    unique_email = f"reuse_profile_{uuid.uuid4()}@example.com"
    initial_password = "SecurePass123!"

    # 1. Register user
    response = client.post('/registro', data={
        'nombre': 'Reuse User',
        'email': unique_email,
        'password': initial_password,
        'confirm_password': initial_password
    })
    assert response.status_code == 302

    # 2. Attempt password change with the SAME password
    response = client.post('/perfil', data={
        'form_name': 'password',
        'current_password': initial_password,
        'password': initial_password,
        'confirm_password': initial_password
    }, follow_redirects=True)

    # 3. Assert error is flashed/returned
    assert b'La nueva contrase\xc3\xb1a no puede ser igual a la contrase\xc3\xb1a actual.' in response.data

    # 4. Assert audit log contains the failure
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == unique_email))
        assert user is not None
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == user.user_id, AuditLog.action == 'CHANGE_PASSWORD', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'reuse_current_password'

def test_password_reset_rejects_reuse(client, app):
    """Verifica que el restablecimiento de contraseña vía token rechace usar la misma contraseña actual."""
    from app.models import get_session_factory, User, AuditLog, crear_reset_token
    unique_email = f"reuse_reset_{uuid.uuid4()}@example.com"
    initial_password = "SecurePass123!"

    # 1. Register user
    client.post('/registro', data={
        'nombre': 'Reset Reuse User',
        'email': unique_email,
        'password': initial_password,
        'confirm_password': initial_password
    })
    client.post('/logout')

    # Get user_id
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == unique_email))
        user_id = user.user_id

    # 2. Create reset token
    token_res = crear_reset_token(user_id, "127.0.0.1")
    assert token_res['success']
    token = token_res['token']

    # 3. Attempt password reset with the SAME password
    response = client.post(f'/reset-password/{token}', data={
        'password': initial_password,
        'confirm_password': initial_password
    }, follow_redirects=True)

    # 4. Assert error is flashed/returned
    assert b'La nueva contrase\xc3\xb1a no puede ser igual a la contrase\xc3\xb1a actual.' in response.data

    # 5. Assert audit log contains the failure
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == user_id, AuditLog.action == 'PASSWORD_RESET', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'reuse_current_password'
