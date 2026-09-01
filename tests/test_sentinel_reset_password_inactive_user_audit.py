import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_inactive_reset_audit.db'
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

def test_reset_password_inactive_user_audit(client):
    """Verifies that attempting reset_password_with_email for an inactive user records a TOKEN_VALIDATION_FAILED audit log."""
    from app.models import get_session_factory, User, crear_reset_token, AuditLog, select
    from werkzeug.security import generate_password_hash

    pw_hash = generate_password_hash("Password123!")
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='inactive_reset_user',
            email='inactive_reset@example.com',
            nombre='InactiveUser',
            password_hash=pw_hash,
            status='inactive'
        )
        db_session.add(user)
        db_session.commit()

    token_res = crear_reset_token('inactive_reset_user', '127.0.0.1')
    raw_token = token_res['token']

    # Access reset password page with token for inactive user
    response = client.get(f'/reset-password/{raw_token}', follow_redirects=True)
    assert response.status_code == 200

    # Verify that a TOKEN_VALIDATION_FAILED audit log was persisted
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'inactive_reset_user',
                AuditLog.action == 'TOKEN_VALIDATION_FAILED',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('reason') == 'user_not_found_or_inactive'
        assert log.details.get('context') == 'reset_password'
