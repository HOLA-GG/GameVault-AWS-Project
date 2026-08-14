import pytest
import uuid
import sys
import os
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin.db'
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


def test_admin_cannot_delete_another_admin(client, app):
    """Verifica que un administrador no pueda eliminar a otro administrador."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    # 1. Crear Administrador A (el que ejecuta la accion)
    admin_a_pw = generate_password_hash("SecureA123!")
    user_a = crear_usuario(
        nombre="Admin A",
        apellido="A",
        email="admin_a@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_a_pw
    )
    assert user_a is not None
    # Cambiar rol a admin en DB
    session_factory = get_session_factory()
    with session_factory() as session:
        db_user_a = session.get(User, user_a['user_id'])
        db_user_a.role = 'admin'
        session.commit()

    # 2. Crear Administrador B (el objetivo)
    admin_b_pw = generate_password_hash("SecureB123!")
    user_b = crear_usuario(
        nombre="Admin B",
        apellido="B",
        email="admin_b@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_b_pw
    )
    assert user_b is not None
    with session_factory() as session:
        db_user_b = session.get(User, user_b['user_id'])
        db_user_b.role = 'admin'
        session.commit()

    # 3. Loguearse como Administrador A
    with client.session_transaction() as sess:
        sess['user_id'] = user_a['user_id']
        sess['email'] = user_a['email']
        sess['nombre'] = user_a['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_a_pw.encode('utf-8')).hexdigest()

    # 4. Intentar eliminar al Administrador B
    response = client.post(f"/admin/delete/{user_b['user_id']}")
    assert response.status_code == 302

    # 5. Verificar que el Administrador B no haya sido eliminado
    with session_factory() as session:
        db_user_b_check = session.get(User, user_b['user_id'])
        assert db_user_b_check is not None
        assert db_user_b_check.role == 'admin'

    # 6. Verificar que se genero un log de auditoria fallido
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == user_a['user_id'], AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('target_user_id') == user_b['user_id']
        assert log.details.get('operation') == 'delete_user'
        assert log.details.get('error') == 'cannot_delete_another_admin'


def test_admin_can_delete_regular_user(client, app):
    """Verifica que un administrador si pueda eliminar a un usuario comun."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    # 1. Crear Administrador A
    admin_pw = generate_password_hash("SecureAdmin1!")
    admin_user = crear_usuario(
        nombre="Admin Single",
        apellido="",
        email="admin_single@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    # 2. Crear Usuario regular
    regular_pw = generate_password_hash("SecureUser1!")
    reg_user = crear_usuario(
        nombre="Regular User",
        apellido="",
        email="regular@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=regular_pw
    )

    # 3. Loguearse como Administrador
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    # 4. Eliminar el usuario regular
    response = client.post(f"/admin/delete/{reg_user['user_id']}")
    assert response.status_code == 302

    # 5. Verificar que el usuario regular fue eliminado
    with session_factory() as session:
        db_reg_check = session.get(User, reg_user['user_id'])
        assert db_reg_check is None

    # 6. Verificar que se genero un log de auditoria exitoso
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_user['user_id'], AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'SUCCESS')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('target_user_id') == reg_user['user_id']
        assert log.details.get('operation') == 'delete_user'


def test_limpiar_logs_antiguos_boundary_handling(app):
    """Verifica que limpiar_logs_antiguos maneje adecuadamente valores extremos y negativos."""
    from app.models import limpiar_logs_antiguos, crear_log_audit

    # Asegurar que limpiar_logs_antiguos se ejecuta correctamente
    # 1. Crear un log ficticio
    crear_log_audit(
        user_id=None,
        action='TEST_LIMIT',
        resource='tests',
        details={'test': True},
        status='SUCCESS'
    )

    # 2. Ejecutar con days=0 (deberia forzarse a 1 dia)
    res_zero = limpiar_logs_antiguos(0)
    assert res_zero['error'] is None

    # 3. Ejecutar con days=-10 (deberia forzarse a 1 dia)
    res_neg = limpiar_logs_antiguos(-10)
    assert res_neg['error'] is None

    # 4. Ejecutar con days=50000 (deberia limitarse a 36500)
    res_large = limpiar_logs_antiguos(50000)
    assert res_large['error'] is None


def test_admin_cannot_edit_another_admin(client, app):
    """Verifica que un administrador no pueda editar/renombrar a otro administrador."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    # 1. Crear Administrador A
    admin_a_pw = generate_password_hash("SecureA123!")
    user_a = crear_usuario(
        nombre="Admin A",
        apellido="A",
        email="admin_a_edit@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_a_pw
    )
    assert user_a is not None
    session_factory = get_session_factory()
    with session_factory() as session:
        db_user_a = session.get(User, user_a['user_id'])
        db_user_a.role = 'admin'
        session.commit()

    # 2. Crear Administrador B
    admin_b_pw = generate_password_hash("SecureB123!")
    user_b = crear_usuario(
        nombre="Admin B",
        apellido="B",
        email="admin_b_edit@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_b_pw
    )
    assert user_b is not None
    with session_factory() as session:
        db_user_b = session.get(User, user_b['user_id'])
        db_user_b.role = 'admin'
        session.commit()

    # 3. Loguearse como Administrador A
    with client.session_transaction() as sess:
        sess['user_id'] = user_a['user_id']
        sess['email'] = user_a['email']
        sess['nombre'] = user_a['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_a_pw.encode('utf-8')).hexdigest()

    # 4. Intentar renombrar al Administrador B
    response = client.post(f"/admin/edit/{user_b['user_id']}", data={'nombre': 'Nombre Alterado'})
    assert response.status_code == 302

    # 5. Verificar que el Administrador B no haya sido renombrado
    with session_factory() as session:
        db_user_b_check = session.get(User, user_b['user_id'])
        assert db_user_b_check is not None
        assert db_user_b_check.nombre == "Admin B"

    # 6. Verificar que se genero un log de auditoria fallido
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == user_a['user_id'], AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('target_user_id') == user_b['user_id']
        assert log.details.get('operation') == 'rename_user'
        assert log.details.get('error') == 'cannot_edit_another_admin'


def test_reset_password_get_rate_limiting(client, app):
    """Verifica que el rate-limiting en solicitudes GET en la ruta de reset password esté activo."""
    from app.extensions import limiter
    # Habilitar rate-limiting para esta prueba específica
    app.config['RATELIMIT_ENABLED'] = True
    limiter.enabled = True

    # Realizar más de 10 peticiones GET consecutivas a reset-password
    # (El límite que colocamos es de 10 por minuto para peticiones GET)
    for i in range(10):
        res = client.get('/reset-password/dummy-token-rate-limit-test')
        # Las primeras peticiones deberían procesarse (redirigiendo o fallando por token no válido)
        assert res.status_code in (200, 302)

    try:
        # El intento número 11 debería ser rechazado con 429 Too Many Requests
        res_limit = client.get('/reset-password/dummy-token-rate-limit-test')
        assert res_limit.status_code == 429
        assert b"Demasiados intentos" in res_limit.data
    finally:
        # Restaurar estado original del limiter
        app.config['RATELIMIT_ENABLED'] = False
        limiter.enabled = False


def test_admin_pagination_boundary_overflow(client, app):
    """Verifica que las rutas administrativas con paginación manejen de forma segura valores extremos de página."""
    from app.models import get_session_factory, User, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    # 1. Crear Administrador
    admin_pw = generate_password_hash("SecureAdmin1!")
    admin_user = crear_usuario(
        nombre="Admin Single",
        apellido="",
        email="admin_boundary@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    session_factory = get_session_factory()
    with session_factory() as session:
        db_admin = session.get(User, admin_user['user_id'])
        db_admin.role = 'admin'
        session.commit()

    # 2. Loguearse como Administrador
    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    # 3. Probar con páginas absurdamente gigantes (que causarían desbordamiento en SQLite/DB)
    bypasses = [
        "10000000000000000000000000000000000000000000000000000",
        "9" * 100
    ]

    for giant_page in bypasses:
        # Ruta de admin panel
        res_admin = client.get(f'/admin?page={giant_page}')
        assert res_admin.status_code == 200

        # Ruta de admin colecciones
        res_collections = client.get(f'/admin/collections?page={giant_page}')
        assert res_collections.status_code == 200
