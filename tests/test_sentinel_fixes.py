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
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
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
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    assert response.status_code == 302

    # Attempt password change with WRONG current password
    client.post('/perfil', data={
        'form_name': 'password',
        'current_password': 'wrong_password',
        'password': 'newSecurePass123!',
        'confirm_password': 'newSecurePass123!'
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
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })
    assert response.status_code == 302

    # Verify we are logged in
    with client.session_transaction() as sess:
        assert sess.get('user_id') is not None

    # Successful password change
    response = client.post('/perfil', data={
        'form_name': 'password',
        'current_password': 'SecurePass123!',
        'password': 'newSecurePass123!',
        'confirm_password': 'newSecurePass123!'
    })

    # Check redirect to login
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/login')

    # Check session is cleared
    with client.session_transaction() as sess:
        assert 'user_id' not in sess
        assert 'email' not in sess

def test_stale_admin_session(client, app):
    """Verifica que un admin degradado pierda acceso al panel en tiempo real."""
    from app.models import get_session_factory, User
    unique_email = f"stale_admin_{uuid.uuid4()}@example.com"
    # 1. Register and login
    client.post('/registro', data={
        'nombre': 'Stale Admin',
        'email': unique_email,
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })

    # 2. Upgrade to admin in DB
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == unique_email))
        user.role = 'admin'
        db_session.commit()

    # Refresh session data (re-login or manual sync) - re-login is cleaner
    client.post('/logout')
    client.post('/login', data={'email': unique_email, 'password': 'SecurePass123!'})

    # Verify admin access
    response = client.get('/admin')
    assert response.status_code == 200

    # 3. Demote in DB
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == unique_email))
        user.role = 'user'
        db_session.commit()

    # 4. Access admin panel with SAME session
    response = client.get('/admin')
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')

def test_deactivated_while_logged_in(client, app):
    """Verifica que un usuario desactivado pierda acceso al dashboard en tiempo real."""
    from app.models import get_session_factory, User
    unique_email = f"deactivated_{uuid.uuid4()}@example.com"
    # 1. Register and login
    client.post('/registro', data={
        'nombre': 'Active User',
        'email': unique_email,
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })

    # Verify access
    response = client.get('/dashboard')
    assert response.status_code == 200

    # 2. Deactivate in DB
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == unique_email))
        user.status = 'inactive'
        db_session.commit()

    # 3. Access dashboard
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')

def test_rate_showcase_hardening_and_audit(client, app):
    """Verifica el endurecimiento y auditoría del endpoint de valoración."""
    from app.models import get_session_factory, AuditLog, select

    # 1. Test invalid input (too long subject_id)
    response = client.post(
        '/api/showcase/rate',
        json={
            'subject_type': 'sample',
            'subject_id': 'a' * 121,
            'rating': 5
        }
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'Datos de valoración inválidos.' in data.get('error', '')

    # Verify audit log for failure
    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == 'RATE_SHOWCASE', AuditLog.status == 'FAILED')
        )
        assert log is not None
        assert log.details.get('reason') == 'invalid_input'
        # Check truncation
        assert len(log.details.get('subject_id')) <= 200

    # 2. Test valid input and audit
    response = client.post(
        '/api/showcase/rate',
        json={
            'subject_type': 'sample',
            'subject_id': 'demo-nintendo-reliquias',
            'rating': 5
        }
    )
    assert response.status_code == 200

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.action == 'RATE_SHOWCASE', AuditLog.status == 'SUCCESS')
        )
        assert log is not None
        assert log.details.get('subject_id') == 'demo-nintendo-reliquias'

def test_rate_showcase_type_safety(client):
    """Verifica que el endpoint maneje correctamente tipos de datos inesperados sin explotar."""
    # Enviar un entero donde se espera un string (subject_type)
    response = client.post(
        '/api/showcase/rate',
        json={
            'subject_type': 123,
            'subject_id': 'valid-id',
            'rating': 5
        }
    )
    assert response.status_code == 400
    data = response.get_json()
    assert 'Datos de valoración inválidos.' in data.get('error', '')


def test_rate_showcase_public_invalid_id(client, app):
    """Verifica que un subject_id público malformado o de longitud/caracteres inválidos sea rechazado."""
    from app.models import get_session_factory, AuditLog, select

    # Enviar un ID de vitrina pública con caracteres no permitidos o longitud incorrecta
    response = client.post(
        '/api/showcase/rate',
        json={
            'subject_type': 'public',
            'subject_id': 'invalid-uuid-with-spaces-and-symbols!!',
            'rating': 5
        }
    )
    assert response.status_code == 404
    data = response.get_json()
    assert 'Colección pública no disponible para portada.' in data.get('error', '')

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.action == 'RATE_SHOWCASE',
                AuditLog.status == 'FAILED',
                AuditLog.details['reason'].as_string() == 'invalid_public_subject_id'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'invalid_public_subject_id'
