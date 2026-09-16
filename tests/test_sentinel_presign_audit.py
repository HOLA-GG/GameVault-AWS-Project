"""Test audit logging for failed presigned upload requests."""

import os
import sys
import hashlib
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_presign_audit.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')
    monkeypatch.setenv('WTF_CSRF_ENABLED', '0')
    monkeypatch.setenv('STORAGE_BACKEND', 'local')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    from app import create_app
    app_instance = create_app()
    app_instance.config['WTF_CSRF_ENABLED'] = False
    app_instance.config['TESTING'] = True
    app_instance.config['STORAGE_BACKEND'] = 'local'

    yield app_instance

    if os.path.exists(db_file):
        os.remove(db_file)


@pytest.fixture
def client(app):
    return app.test_client()


def test_presign_upload_audit_on_failure(client, app):
    from app.models import crear_usuario, obtener_todos_logs
    from werkzeug.security import generate_password_hash

    pw_hash = generate_password_hash('Password123!')
    user = crear_usuario('Test User', '', 'user@example.com', '+57', '3001234567', pw_hash)

    # Login via session with user-agent and pw_hash pinning
    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()
        sess['_user_agent'] = 'werkzeug/3.1.3'

    # 1. Test disallowed file extension
    resp1 = client.post(
        '/api/uploads/presign',
        json={'filename': 'malicious.exe', 'content_type': 'image/jpeg'},
        headers={'User-Agent': 'werkzeug/3.1.3'},
    )
    assert resp1.status_code == 400

    # 2. Test invalid parameter length
    resp2 = client.post(
        '/api/uploads/presign',
        json={'filename': 'a' * 300, 'content_type': 'image/jpeg'},
        headers={'User-Agent': 'werkzeug/3.1.3'},
    )
    assert resp2.status_code == 400

    # 3. Test missing/None parameters
    resp3 = client.post(
        '/api/uploads/presign',
        json={'filename': None, 'content_type': None},
        headers={'User-Agent': 'werkzeug/3.1.3'},
    )
    assert resp3.status_code == 400

    # Verify audit log entries were recorded
    logs = obtener_todos_logs({'action': 'PRESIGNED_UPLOAD_FAILED'})
    assert len(logs) >= 3

    disallowed_type_log = next(
        (log for log in logs if log.get('details', {}).get('reason') == 'disallowed_file_type'),
        None,
    )
    assert disallowed_type_log is not None
    assert disallowed_type_log['status'] == 'FAILED'

    invalid_params_log = next(
        (log for log in logs if log.get('details', {}).get('reason') == 'invalid_parameters'),
        None,
    )
    assert invalid_params_log is not None
    assert invalid_params_log['status'] == 'FAILED'


def test_presign_upload_audit_storage_disabled(client, app):
    from app.models import crear_usuario, obtener_todos_logs
    from werkzeug.security import generate_password_hash

    app.config['STORAGE_BACKEND'] = 'none'

    pw_hash = generate_password_hash('Password123!')
    user = crear_usuario('Test User 2', '', 'user2@example.com', '+57', '3001234568', pw_hash)

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()
        sess['_user_agent'] = 'werkzeug/3.1.3'

    resp = client.post(
        '/api/uploads/presign',
        json={'filename': 'cover.jpg', 'content_type': 'image/jpeg'},
        headers={'User-Agent': 'werkzeug/3.1.3'},
    )
    assert resp.status_code == 503

    logs = obtener_todos_logs({'action': 'PRESIGNED_UPLOAD_FAILED'})
    disabled_log = next(
        (log for log in logs if log.get('details', {}).get('reason') == 'storage_disabled'),
        None,
    )
    assert disabled_log is not None
    assert disabled_log['status'] == 'FAILED'
