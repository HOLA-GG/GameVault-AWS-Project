import pytest
import sys
import os
import hashlib
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_admin_clear.db'
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
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()


def test_admin_logs_clear_boundary_inputs(client, app):
    """Verifica que el endpoint /admin/logs/clear limite de forma segura los valores de 'dias'."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    # 1. Crear Administrador
    admin_pw = generate_password_hash("SecureAdmin1!")
    admin_user = crear_usuario(
        nombre="Admin Clear",
        apellido="",
        email="admin_clear@example.com",
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

    test_cases = [
        ("0", 1),
        ("-10", 1),
        ("9" * 100, 36500),
        ("abc", 7),
    ]

    for input_dias, expected_dias in test_cases:
        response = client.post('/admin/logs/clear', data={'dias': input_dias})
        assert response.status_code == 302

        with session_factory() as session:
            log = session.scalar(
                select(AuditLog)
                .where(AuditLog.user_id == admin_user['user_id'], AuditLog.action == 'ADMIN_ACTION')
                .order_by(AuditLog.timestamp.desc())
            )
            assert log is not None
            assert log.details.get('operation') == 'clear_logs'
            assert log.details.get('days') == expected_dias
