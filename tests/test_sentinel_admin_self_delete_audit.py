import pytest
import os
import sys
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_self_delete_audit.db'
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

def test_admin_cannot_delete_self_audit_logged(client, app):
    """Verifica que intentar eliminar la propia cuenta de admin registre un log de auditoría fallido."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    admin_pw = generate_password_hash("SecureAdminSelf1!")
    user_admin = crear_usuario(
        nombre="Admin Self",
        apellido="Delete",
        email="admin_self_delete@example.com",
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

    response = client.post(f"/admin/delete/{user_admin['user_id']}")
    assert response.status_code == 302

    with session_factory() as session:
        db_user_check = session.get(User, user_admin['user_id'])
        assert db_user_check is not None

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user_admin['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('target_user_id') == user_admin['user_id']
        assert log.details.get('operation') == 'delete_user'
        assert log.details.get('error') == 'cannot_delete_self'
