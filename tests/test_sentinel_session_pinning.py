import pytest
import sys
import os
import hashlib
from sqlalchemy import select
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_session_pinning.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app components
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

def test_session_user_agent_pinning_success(client):
    """Verifies that normal access works when User-Agent matches the pinned value."""
    # Register and log in
    client.post('/registro', data={
        'nombre': 'Session User',
        'email': 'pinning@example.com',
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    }, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})

    # Legitimate request with the same User-Agent
    response = client.get('/dashboard', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    assert response.status_code == 200
    assert b'Mi colecci' in response.data

def test_session_user_agent_pinning_mismatch_failure(client):
    """Verifies that changing the User-Agent mid-session invalidates the session and logs the event."""
    # Register and log in with Browser A User-Agent
    client.post('/registro', data={
        'nombre': 'Session User 2',
        'email': 'pinning2@example.com',
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    }, headers={'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'})

    # Malicious request with hijacked session cookie but Browser B User-Agent
    response = client.get('/dashboard', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}, follow_redirects=True)
    assert response.status_code == 200
    # Should redirect to login page with a flash message
    assert b'Tu sesi\xc3\xb3n ha sido invalidada por un cambio de dispositivo o navegador.' in response.data

    # Verify that session is cleared
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

    # Verify that an audit log of the UNAUTHORIZED_ACCESS with user_agent_mismatch was created
    from app.models import get_session_factory, AuditLog
    session_factory = get_session_factory()
    with session_factory() as db_session:
        logs = db_session.scalars(
            select(AuditLog).where(
                AuditLog.action == 'UNAUTHORIZED_ACCESS'
            ).order_by(AuditLog.timestamp.desc())
        ).all()
        assert len(logs) > 0
        details = logs[0].details
        assert details.get('reason') == 'user_agent_mismatch'
        assert details.get('stored_ua') == 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X)'
        assert details.get('current_ua') == 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'
