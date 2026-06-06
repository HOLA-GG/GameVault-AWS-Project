import pytest
import uuid
import sys
import importlib
import os
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    # Use a truly unique database per test run or just a dedicated file
    db_file = 'gamevault_test_sentinel.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

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
        "RATELIMIT_ENABLED": False,
    })

    yield flask_app

    # Cleanup after all tests in this file
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_registration_clears_session(client):
    """Verifica que el registro limpie cualquier dato previo en la sesión (prevención de fixation)."""
    unique_email = f"sentinel_{uuid.uuid4()}@example.com"
    with client.session_transaction() as sess:
        sess['fixation_attempt'] = 'malicious_value'

    response = client.post('/registro', data={
        'nombre': 'Sentinel User',
        'email': unique_email,
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 302

    with client.session_transaction() as sess:
        assert 'fixation_attempt' not in sess
        assert sess['email'] == unique_email

def test_password_change_failure_logs_audit(client, app):
    """Verifica que el fallo al cambiar contraseña genere un log de auditoría."""
    from app.models import get_session_factory, User, AuditLog
    unique_email = f"audit_{uuid.uuid4()}@example.com"
    # Register and login
    response = client.post('/registro', data={
        'nombre': 'Audit User',
        'email': unique_email,
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 302

    # Attempt password change with WRONG current password
    client.post('/perfil', data={
        'form_name': 'password',
        'current_password': 'wrong_password',
        'password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })

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
        assert log.details.get('reason') == 'incorrect_current_password'

def test_password_change_success_clears_session_and_redirects(client):
    """Verifica que un cambio de contraseña exitoso invalide la sesión y redirija al login."""
    unique_email = f"success_{uuid.uuid4()}@example.com"
    # Register and login
    response = client.post('/registro', data={
        'nombre': 'Success User',
        'email': unique_email,
        'password': 'password123',
        'confirm_password': 'password123'
    })
    assert response.status_code == 302

    # Verify we are logged in
    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None

    # Successful password change
    response = client.post('/perfil', data={
        'form_name': 'password',
        'current_password': 'password123',
        'password': 'newpassword123',
        'confirm_password': 'newpassword123'
    })

    # Check redirect to login
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')

    # Check session is cleared
    with client.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'email' not in sess
