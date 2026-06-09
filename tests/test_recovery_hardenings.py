import pytest
import uuid
import sys
import os
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_recovery.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload
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

def test_inactive_user_cannot_initiate_recovery_email(client, app):
    """Verifica que un usuario inactivo no pueda iniciar la recuperación por email."""
    from app.models import crear_usuario, get_session_factory, User
    email = "inactive_email@example.com"
    crear_usuario("Inactive", "User", email, "", "", "hash")

    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == email))
        user.status = 'inactive'
        db_session.commit()

    response = client.post('/forgot-password', data={'email': email}, follow_redirects=True)
    assert response.status_code == 200
    from app.models import PasswordResetToken
    with session_factory() as db_session:
        tokens = db_session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.user_id)).all()
        assert len(tokens) == 0

def test_inactive_user_cannot_initiate_recovery_manual_token(client, app):
    """Verifica que un usuario inactivo no pueda iniciar la recuperación por token manual."""
    from app.models import crear_usuario, get_session_factory, User, PasswordResetToken
    email = "inactive_manual@example.com"
    telefono = "123456789"
    crear_usuario("Inactive", "Manual", email, "", telefono, "hash")

    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == email))
        user.status = 'inactive'
        db_session.commit()

    app.config['SHOW_RESET_DEBUG_TOKEN'] = True
    response = client.post('/forgot-password/manual-token', data={'email': email, 'telefono': telefono})
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/forgot-password')

    with session_factory() as db_session:
        tokens = db_session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user.user_id)).all()
        assert len(tokens) == 0

def test_reset_password_get_fails_for_inactive_user(client, app):
    """Verifica que el formulario de reset falle si el usuario fue desactivado tras generar el token."""
    from app.models import crear_usuario, crear_reset_token, get_session_factory, User
    email = "deactivated_mid_flow@example.com"
    u = crear_usuario("Deactivated", "Flow", email, "", "", "hash")
    token = crear_reset_token(u['user_id'])['token']

    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.user_id == u['user_id']))
        user.status = 'inactive'
        db_session.commit()

    response = client.get(f'/reset-password/{token}')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/forgot-password')

def test_reset_password_post_fails_for_inactive_user(client, app):
    """Verifica que el reset final falle si el usuario está inactivo."""
    from app.models import crear_usuario, crear_reset_token, get_session_factory, User
    email = "deactivated_post@example.com"
    u = crear_usuario("Deactivated", "Post", email, "", "", "hash")
    token = crear_reset_token(u['user_id'])['token']

    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.user_id == u['user_id']))
        user.status = 'inactive'
        db_session.commit()

    response = client.post(f'/reset-password/{token}', data={
        'password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/forgot-password')

def test_session_cleared_after_password_reset(client, app):
    """Verifica que la sesión se limpie tras un reset de contraseña exitoso."""
    from app.models import crear_usuario, crear_reset_token
    email = "session_clear@example.com"
    u = crear_usuario("Session", "Clear", email, "", "", "hash")
    token = crear_reset_token(u['user_id'])['token']

    with client.session_transaction() as sess:
        sess['junk_data'] = 'to_be_cleared'

    response = client.post(f'/reset-password/{token}', data={
        'password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')

    with client.session_transaction() as sess:
        assert 'junk_data' not in sess
