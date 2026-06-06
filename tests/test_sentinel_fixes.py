import pytest
import uuid
from app import create_app
from app.models import get_session_factory, User, AuditLog, get_engine
from sqlalchemy import select

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_registration_clears_session(client):
    """Verifica que el registro limpie cualquier dato previo en la sesión (prevención de fixation)."""
    unique_email = f"sentinel_{uuid.uuid4()}@example.com"
    with client.session_transaction() as sess:
        sess['fixation_attempt'] = 'malicious_value'

    client.post('/registro', data={
        'nombre': 'Sentinel User',
        'email': unique_email,
        'password': 'password123',
        'confirm_password': 'password123'
    })

    with client.session_transaction() as sess:
        assert 'fixation_attempt' not in sess
        assert sess['email'] == unique_email

def test_password_change_failure_logs_audit(client, app):
    """Verifica que el fallo al cambiar contraseña genere un log de auditoría."""
    unique_email = f"audit_{uuid.uuid4()}@example.com"
    # Register and login
    client.post('/registro', data={
        'nombre': 'Audit User',
        'email': unique_email,
        'password': 'password123',
        'confirm_password': 'password123'
    })

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
    client.post('/registro', data={
        'nombre': 'Success User',
        'email': unique_email,
        'password': 'password123',
        'confirm_password': 'password123'
    })

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
