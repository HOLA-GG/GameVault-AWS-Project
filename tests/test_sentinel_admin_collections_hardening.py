import hashlib
import os
import sys
import pytest
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin_col.db'
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
        except Exception:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


def test_admin_collections_exception_handling(client, app, monkeypatch):
    """Verifica que si ocurre un error de base de datos en admin_collections se registre en auditoría y redirija de forma segura."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    # 1. Crear usuario Administrador
    admin_pw = generate_password_hash("SecureAdminCol1!")
    admin_user = crear_usuario(
        nombre="Admin Col",
        apellido="Tester",
        email="admin_col_test@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=admin_pw
    )
    assert admin_user is not None

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

    # 3. Simular una excepción en contar_resumenes_colecciones
    def mock_contar_error(visibility=None):
        raise RuntimeError("Error simulado de base de datos en contar_resumenes_colecciones")

    monkeypatch.setattr('app.routes.contar_resumenes_colecciones', mock_contar_error)

    # 4. Realizar la petición GET a /admin/collections
    response = client.get('/admin/collections?visibility=public')

    # 5. Verificar que se realiza redirección 302 a /admin
    assert response.status_code == 302
    assert response.location.endswith('/admin')

    # 6. Verificar que se creó un log de auditoría con status='FAILED'
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == admin_user['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.resource == 'collections',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'view_collections'
        assert log.details.get('visibility') == 'public'
        assert 'Error simulado' in log.details.get('error', '')
