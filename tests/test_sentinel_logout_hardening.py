import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_logout_hardening.db'
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


def test_logout_exception_handling_clears_session(client, monkeypatch):
    from flask import session
    from app.models import crear_usuario
    from werkzeug.security import generate_password_hash

    # Create active user
    pw_hash = generate_password_hash('Password123!')
    user = crear_usuario('Test Logout User', '', 'logout_test@example.com', '', '', pw_hash)

    headers = {'User-Agent': 'TestBrowser/1.0'}

    # Simulate logged in session
    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        import hashlib
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()
        sess['_user_agent'] = 'TestBrowser/1.0'

    # Verify session is populated
    with client:
        res = client.get('/dashboard', headers=headers)
        assert res.status_code == 200
        assert session.get('user_id') == user['user_id']

    # Mock crear_log_audit to raise an exception on first call during logout
    import app.routes
    original_crear_log_audit = app.routes.crear_log_audit
    call_count = 0

    def mock_crear_log_audit(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("Database connection lost during audit logging")
        return original_crear_log_audit(*args, **kwargs)

    monkeypatch.setattr(app.routes, 'crear_log_audit', mock_crear_log_audit)

    with client:
        response = client.post('/logout', headers=headers, follow_redirects=True)
        assert response.status_code == 200
        # Verify session is invalidated even when exception occurs
        assert session.get('user_id') is None
