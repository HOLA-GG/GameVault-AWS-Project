import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_password_reset_audit.db'
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

def test_password_reset_validation_failure_audited(client):
    """Verifies that a failed password reset form submission generates a FAILED audit log."""
    from app.models import get_session_factory, User, crear_reset_token, AuditLog, select
    from werkzeug.security import generate_password_hash

    pw_hash = generate_password_hash("OldPassword123!")
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='reset_audit_user',
            email='reset_audit@example.com',
            nombre='AuditUser',
            password_hash=pw_hash,
            status='active'
        )
        db_session.add(user)
        db_session.commit()

    token_res = crear_reset_token('reset_audit_user', '127.0.0.1')
    raw_token = token_res['token']

    # Submit invalid new password (weak password, missing uppercase/number)
    response = client.post(f'/reset-password/{raw_token}', data={
        'password': 'weak',
        'confirm_password': 'weak'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'La contrase\xc3\xb1a debe tener entre 8 y 128 caracteres' in response.data or b'error' in response.data

    # Verify that a FAILED audit log was persisted
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'reset_audit_user',
                AuditLog.action == 'PASSWORD_RESET',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('email') == 'reset_audit@example.com'
        assert 'errors' in log.details

def test_password_reset_mismatch_failure_audited(client):
    """Verifies that password confirmation mismatch generates a FAILED audit log."""
    from app.models import get_session_factory, User, crear_reset_token, AuditLog, select
    from werkzeug.security import generate_password_hash

    pw_hash = generate_password_hash("OldPassword123!")
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='reset_audit_user2',
            email='reset_audit2@example.com',
            nombre='AuditUser2',
            password_hash=pw_hash,
            status='active'
        )
        db_session.add(user)
        db_session.commit()

    token_res = crear_reset_token('reset_audit_user2', '127.0.0.1')
    raw_token = token_res['token']

    # Submit mismatched passwords
    response = client.post(f'/reset-password/{raw_token}', data={
        'password': 'NewPassword123!',
        'confirm_password': 'DifferentPassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Las contrase\xc3\xb1as no coinciden.' in response.data

    # Verify that a FAILED audit log was persisted
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'reset_audit_user2',
                AuditLog.action == 'PASSWORD_RESET',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('email') == 'reset_audit2@example.com'
        assert any('coinciden' in err for err in log.details.get('errors', []))

def test_token_creation_failure_audited_forgot_password(client, monkeypatch):
    """Verifies that a failed token creation in forgot_password records a FAILED audit log."""
    from app.models import get_session_factory, User, AuditLog, select
    from werkzeug.security import generate_password_hash

    pw_hash = generate_password_hash("OldPassword123!")
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='reset_audit_user3',
            email='reset_audit3@example.com',
            nombre='AuditUser3',
            password_hash=pw_hash,
            status='active'
        )
        db_session.add(user)
        db_session.commit()

    import app.routes
    monkeypatch.setattr(app.routes, 'crear_reset_token', lambda user_id, ip: {'success': False, 'error': 'db_error'})

    response = client.post('/forgot-password', data={'email': 'reset_audit3@example.com'}, follow_redirects=True)
    assert response.status_code == 200

    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'reset_audit_user3',
                AuditLog.action == 'PASSWORD_RESET_REQUEST',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('email') == 'reset_audit3@example.com'
        assert log.details.get('reason') == 'token_creation_failed'

def test_token_creation_failure_audited_forgot_password_manual(client, monkeypatch):
    """Verifies that a failed token creation in forgot_password_manual records a FAILED audit log."""
    from app.models import get_session_factory, User, AuditLog, select
    from werkzeug.security import generate_password_hash

    pw_hash = generate_password_hash("OldPassword123!")
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='reset_audit_user4',
            email='reset_audit4@example.com',
            nombre='AuditUser4',
            telefono='1234567890',
            password_hash=pw_hash,
            status='active'
        )
        db_session.add(user)
        db_session.commit()

    import app.routes
    monkeypatch.setattr(app.routes, 'crear_reset_token', lambda user_id, ip: {'success': False, 'error': 'db_error'})

    response = client.post('/forgot-password/manual', data={'email': 'reset_audit4@example.com', 'telefono': '1234567890'}, follow_redirects=True)
    assert response.status_code == 200

    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'reset_audit_user4',
                AuditLog.action == 'PASSWORD_RESET_REQUEST',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('email') == 'reset_audit4@example.com'
        assert log.details.get('channel') == 'manual_token'
        assert log.details.get('reason') == 'token_creation_failed'
