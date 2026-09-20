"""Tests para verificar que los fallos de actualización de perfil y contraseña registren auditoría FAILED."""

import pytest
import hashlib
import importlib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def test_app(monkeypatch):
    db_path = PROJECT_ROOT / 'gamevault_test_profile_audit.db'
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_path}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')
    monkeypatch.setenv('WTF_CSRF_ENABLED', 'false')

    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    app_module = importlib.import_module('app')
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })

    yield flask_app

    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


def test_profile_update_validation_failure_creates_audit_log(test_app):
    """Verifica que un fallo de validación al actualizar el perfil cree un registro de auditoría FAILED."""
    from app.models import crear_usuario, obtener_logs_por_usuario

    with test_app.app_context():
        user = crear_usuario("Profile User", "", "profile_audit_test@example.com", "", "", "Password123!")
        user_id = user["user_id"]
        pw_hash = hashlib.sha256(user["password_hash"].encode('utf-8')).hexdigest()

    client = test_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = "profile_audit_test@example.com"
        sess['nombre'] = "Profile User"
        sess['role'] = "user"
        sess['_pw_hash'] = pw_hash
        sess['_user_agent'] = "test-agent"

    # Enviar solicitud con teléfono inválido (menos de 7 dígitos)
    response = client.post(
        '/perfil',
        data={
            'form_name': 'profile',
            'nombre': 'Profile User',
            'apellido': 'Test',
            'telefono': '123',  # Inválido
            'collection_visibility': 'private',
        },
        headers={'User-Agent': 'test-agent'},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with test_app.app_context():
        logs = obtener_logs_por_usuario(user_id)
        failed_profile_logs = [
            l for l in logs if l['action'] == 'UPDATE_PROFILE' and l['status'] == 'FAILED'
        ]
        assert len(failed_profile_logs) == 1
        assert failed_profile_logs[0]['details']['email'] == "profile_audit_test@example.com"
        assert 'errors' in failed_profile_logs[0]['details']


def test_profile_update_db_failure_creates_audit_log(test_app, monkeypatch):
    """Verifica que un error de base de datos al actualizar perfil genere un log FAILED."""
    from app.models import crear_usuario, obtener_logs_por_usuario
    import app.routes

    with test_app.app_context():
        user = crear_usuario("Profile User DB", "", "profile_db_audit@example.com", "", "", "Password123!")
        user_id = user["user_id"]
        pw_hash = hashlib.sha256(user["password_hash"].encode('utf-8')).hexdigest()

    # Forzar que actualizar_usuario_perfil devuelva success=False
    monkeypatch.setattr(
        app.routes,
        'actualizar_usuario_perfil',
        lambda uid, data: {'success': False, 'error': 'Database write failed'},
    )

    client = test_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = "profile_db_audit@example.com"
        sess['nombre'] = "Profile User DB"
        sess['role'] = "user"
        sess['_pw_hash'] = pw_hash
        sess['_user_agent'] = "test-agent"

    response = client.post(
        '/perfil',
        data={
            'form_name': 'profile',
            'nombre': 'Valid Name',
            'apellido': 'Valid Surname',
            'telefono': '5551234567',
            'collection_visibility': 'private',
        },
        headers={'User-Agent': 'test-agent'},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with test_app.app_context():
        logs = obtener_logs_por_usuario(user_id)
        failed_db_logs = [
            l for l in logs if l['action'] == 'UPDATE_PROFILE' and l['status'] == 'FAILED'
        ]
        assert len(failed_db_logs) == 1
        assert failed_db_logs[0]['details']['reason'] == 'db_update_failed'


def test_password_change_db_failure_creates_audit_log(test_app, monkeypatch):
    """Verifica que un error de base de datos al cambiar la contraseña genere un log FAILED."""
    from app.models import crear_usuario, obtener_logs_por_usuario
    from werkzeug.security import generate_password_hash
    import app.routes

    with test_app.app_context():
        user = crear_usuario("Password User DB", "", "pw_db_audit@example.com", "", "", generate_password_hash("OldPassword123!"))
        user_id = user["user_id"]
        pw_hash = hashlib.sha256(user["password_hash"].encode('utf-8')).hexdigest()

    # Forzar que actualizar_password_usuario devuelva success=False
    monkeypatch.setattr(
        app.routes,
        'actualizar_password_usuario',
        lambda uid, new_hash: {'success': False, 'error': 'Password update failed'},
    )

    client = test_app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = "pw_db_audit@example.com"
        sess['nombre'] = "Password User DB"
        sess['role'] = "user"
        sess['_pw_hash'] = pw_hash
        sess['_user_agent'] = "test-agent"

    response = client.post(
        '/perfil',
        data={
            'form_name': 'password',
            'current_password': 'OldPassword123!',
            'password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!',
        },
        headers={'User-Agent': 'test-agent'},
        follow_redirects=True,
    )

    assert response.status_code == 200

    with test_app.app_context():
        logs = obtener_logs_por_usuario(user_id)
        failed_pw_logs = [
            l for l in logs if l['action'] == 'CHANGE_PASSWORD' and l['status'] == 'FAILED' and l['details'].get('reason') == 'db_update_failed'
        ]
        assert len(failed_pw_logs) == 1
