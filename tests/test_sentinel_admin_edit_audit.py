import hashlib
import os
import sys
import pytest
from sqlalchemy import select


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin_edit_audit.db'
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


def test_admin_edit_user_invalid_id_audit(client, app):
    """Verifica que editar un ID de usuario inválido registre un audit log fallido."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdmin123!")
    admin_user = crear_usuario(
        nombre="Admin Audit",
        apellido="Test",
        email="admin_edit_audit@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    response = client.post("/admin/edit/invalid_id!@#$", data={'nombre': 'Nuevo Nombre'})
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == admin_user['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'rename_user'
        assert log.details.get('error') == 'invalid_user_id'


def test_admin_edit_user_empty_name_audit(client, app):
    """Verifica que intentar asignar un nombre vacío registre un audit log fallido."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdmin123!")
    admin_user = crear_usuario(
        nombre="Admin Audit",
        apellido="Test",
        email="admin_empty_name@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    reg_pw = generate_password_hash("SecureUser123!")
    target_user = crear_usuario(
        nombre="Target User",
        apellido="",
        email="target_user@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=reg_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    response = client.post(f"/admin/edit/{target_user['user_id']}", data={'nombre': '   '})
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == admin_user['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'rename_user'
        assert log.details.get('error') == 'empty_name'


def test_admin_edit_user_name_too_long_audit(client, app):
    """Verifica que intentar asignar un nombre demasiado largo (>120 chars) registre un audit log fallido."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdmin123!")
    admin_user = crear_usuario(
        nombre="Admin Audit",
        apellido="Test",
        email="admin_long_name@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    reg_pw = generate_password_hash("SecureUser123!")
    target_user = crear_usuario(
        nombre="Target User 2",
        apellido="",
        email="target_user2@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=reg_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    long_name = "A" * 121
    response = client.post(f"/admin/edit/{target_user['user_id']}", data={'nombre': long_name})
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == admin_user['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'rename_user'
        assert log.details.get('error') == 'name_too_long'


def test_admin_delete_user_invalid_id_audit(client, app):
    """Verifica que eliminar con un ID de usuario inválido registre un audit log fallido."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdmin123!")
    admin_user = crear_usuario(
        nombre="Admin Audit",
        apellido="Test",
        email="admin_del_invalid@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    response = client.post("/admin/delete/invalid_id!@#$")
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == admin_user['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'delete_user'
        assert log.details.get('error') == 'invalid_user_id'
