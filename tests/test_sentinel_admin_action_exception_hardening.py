import pytest
import sys
import os
import hashlib
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin_action_exc.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    from app.extensions import limiter
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })
    limiter.enabled = False

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()


def test_admin_delete_user_exception_handling(client, app, monkeypatch):
    """Verifica que si ocurre una excepción inesperada durante la eliminación de usuario, se capture y se registre auditoría FAILED."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    import app.routes
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdminDelExc1!")
    admin_user = crear_usuario(
        nombre="Admin Del Exc",
        apellido="",
        email="admin_del_exc@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    reg_pw = generate_password_hash("RegularUserExc1!")
    reg_user = crear_usuario(
        nombre="Regular User Exc",
        apellido="",
        email="reg_del_exc@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=reg_pw
    )

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    # Simulate unexpected failure during eliminar_usuario
    def mock_eliminar_usuario_crash(uid):
        raise RuntimeError("database connection crashed during delete")

    monkeypatch.setattr(app.routes, 'eliminar_usuario', mock_eliminar_usuario_crash)

    response = client.post(f"/admin/delete/{reg_user['user_id']}")
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_user['user_id'], AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'delete_user'
        assert 'database connection crashed' in log.details.get('error', '')


def test_admin_edit_user_exception_handling(client, app, monkeypatch):
    """Verifica que si ocurre una excepción inesperada durante la edición de usuario, se capture y se registre auditoría FAILED."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    import app.routes
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdminEditExc1!")
    admin_user = crear_usuario(
        nombre="Admin Edit Exc",
        apellido="",
        email="admin_edit_exc@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    reg_pw = generate_password_hash("RegularUserEdit1!")
    reg_user = crear_usuario(
        nombre="Regular User Edit",
        apellido="",
        email="reg_edit_exc@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=reg_pw
    )

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    def mock_actualizar_usuario_nombre_crash(uid, nombre):
        raise RuntimeError("database lock timeout during update")

    monkeypatch.setattr(app.routes, 'actualizar_usuario_nombre', mock_actualizar_usuario_nombre_crash)

    response = client.post(f"/admin/edit/{reg_user['user_id']}", data={'nombre': 'Nuevo Nombre Exc'})
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_user['user_id'], AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'rename_user'
        assert 'database lock timeout' in log.details.get('error', '')


def test_admin_logs_clear_uncaught_exception_handling(client, app, monkeypatch):
    """Verifica que si ocurre una excepción no capturada en admin_logs_clear, se capture y se registre auditoría FAILED."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    import app.routes
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdminClearExc1!")
    admin_user = crear_usuario(
        nombre="Admin Clear Exc",
        apellido="",
        email="admin_clear_exc@example.com",
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

    def mock_limpiar_logs_antiguos_crash(days):
        raise RuntimeError("unexpected table lock during clear")

    monkeypatch.setattr(app.routes, 'limpiar_logs_antiguos', mock_limpiar_logs_antiguos_crash)

    response = client.post('/admin/logs/clear', data={'dias': '14'})
    assert response.status_code == 302

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_user['user_id'], AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'clear_logs'
        assert 'unexpected table lock' in log.details.get('error', '')
