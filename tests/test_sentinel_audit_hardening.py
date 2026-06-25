import pytest
import sys
import os
from pathlib import Path
import hashlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_audit_hardening.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

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

def test_unauthorized_access_audit_log(client, app):
    from app.models import obtener_todos_logs, crear_usuario, generate_password_hash

    # 1. Crear un usuario regular
    pw_hash = generate_password_hash('password123')
    user = crear_usuario('Regular User', '', 'regular@example.com', '', '', pw_hash)

    # 2. Iniciar sesión como usuario regular
    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Intentar acceder a una ruta admin
    response = client.get('/admin', follow_redirects=True)
    assert b'Acceso denegado. Solo administradores.' in response.data

    # 4. Verificar que se registró el log de UNAUTHORIZED_ACCESS
    logs = obtener_todos_logs({'action': 'UNAUTHORIZED_ACCESS'})
    assert len(logs) > 0
    assert logs[0]['status'] == 'FAILED'
    assert logs[0]['user_id'] == user['user_id']
    assert 'admin' in logs[0]['details']['target_url']

def test_csrf_failure_audit_log(client, app):
    from app.models import obtener_todos_logs

    # 1. Habilitar CSRF
    app.config['WTF_CSRF_ENABLED'] = True

    # 2. POST sin token CSRF
    response = client.post('/login', data={'email': 'any@test.com', 'password': 'any'})
    assert response.status_code == 400

    # 3. Verificar que se registró el log de CSRF_FAILURE
    logs = obtener_todos_logs({'action': 'CSRF_FAILURE'})
    assert len(logs) > 0
    assert logs[0]['status'] == 'FAILED'
    assert 'csrf' in logs[0]['details']['reason'].lower()

def test_token_validation_failed_audit_log(client, app):
    from app.models import obtener_todos_logs

    # 1. Intentar verificar un token inválido
    client.post('/verify-token', data={'token': 'invalid-token-123'})

    # 2. Intentar resetear password con token inválido
    client.get('/reset-password/another-invalid-token')

    # 3. Verificar que se registraron los logs de TOKEN_VALIDATION_FAILED
    logs = obtener_todos_logs({'action': 'TOKEN_VALIDATION_FAILED'})
    assert len(logs) >= 2
    statuses = [l['status'] for l in logs]
    assert all(s == 'FAILED' for s in statuses)

    contexts = [l['details']['context'] for l in logs]
    assert 'verify_token' in contexts
    assert 'reset_password' in contexts

def test_redaction_extended(client, app):
    from app.models import crear_log_audit, obtener_todos_logs

    details = {
        'my_password': 'secret123',
        'user_session': 'session-id-456',
        'api_key': 'api-789',
        'jwt_token': 'jwt-abc',
        'cookie_data': 'cookie-def',
        'private_info': 'hidden',
        'normal_field': 'visible'
    }

    crear_log_audit(user_id=None, action='TEST_REDACTION', resource='test', details=details)

    logs = obtener_todos_logs({'action': 'TEST_REDACTION'})
    assert len(logs) > 0
    log_details = logs[0]['details']

    assert log_details['my_password'] == '[REDACTED]'
    assert log_details['user_session'] == '[REDACTED]'
    assert log_details['api_key'] == '[REDACTED]'
    assert log_details['jwt_token'] == '[REDACTED]'
    assert log_details['cookie_data'] == '[REDACTED]'
    assert log_details['private_info'] == '[REDACTED]'
    assert log_details['normal_field'] == 'visible'
