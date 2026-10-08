import os
import sys
import hashlib
import pytest
from unittest.mock import patch
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin_logs.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

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
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_admin_logs_exception_handling_and_audit(client, app):
    """Verifica que errores durante la visualización de admin_logs sean capturados, auditados como FAILED y redirigidos a /admin."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdmin123!")
    user_admin = crear_usuario(
        nombre="Admin Logs Test",
        apellido="Tester",
        email="admin_logs_test@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    assert user_admin is not None

    session_factory = get_session_factory()
    with session_factory() as session:
        db_user = session.get(User, user_admin['user_id'])
        db_user.role = 'admin'
        session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = user_admin['user_id']
        sess['email'] = user_admin['email']
        sess['nombre'] = user_admin['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    # Simular una excepción en obtener_todos_logs durante el renderizado de /admin/logs
    with patch('app.routes.obtener_todos_logs', side_effect=RuntimeError('Simulated Database Error')):
        response = client.get('/admin/logs')
        # Debe redirigir a /admin en lugar de un error 500
        assert response.status_code == 302
        assert '/admin' in response.headers.get('Location', '')

    # Verificar que se registró un log de auditoría FAILED
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user_admin['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.resource == 'audit_logs',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'view_logs'
        assert 'Simulated Database Error' in log.details.get('error', '')
