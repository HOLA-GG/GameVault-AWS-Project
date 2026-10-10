import hashlib
import os
import sys
import pytest
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin_panel.db'
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


def test_admin_panel_exception_handling(client, app, monkeypatch):
    """Verifica que si ocurre un error de base de datos en admin_panel se registre en auditoría y redirija de forma segura."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    admin_pw = generate_password_hash("SecureAdminPanel1!")
    admin_user = crear_usuario(
        nombre="Admin Panel",
        apellido="Tester",
        email="admin_panel_test@example.com",
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

    with client.session_transaction() as sess:
        sess['user_id'] = admin_user['user_id']
        sess['email'] = admin_user['email']
        sess['nombre'] = admin_user['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    def mock_contar_error():
        raise RuntimeError("Error simulado de base de datos en contar_usuarios")

    monkeypatch.setattr('app.routes.contar_usuarios', mock_contar_error)

    response = client.get('/admin')

    assert response.status_code == 302
    assert response.location.endswith('/') or response.location.endswith('/landing') or response.location.endswith('/dashboard')

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == admin_user['user_id'],
                AuditLog.action == 'ADMIN_ACTION',
                AuditLog.resource == 'users',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'view_admin_panel'
        assert 'Error simulado' in log.details.get('error', '')
