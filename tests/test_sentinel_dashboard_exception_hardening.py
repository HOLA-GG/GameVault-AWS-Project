import hashlib
import os
import sys
import pytest
from sqlalchemy import select

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_dashboard.db'
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


def test_dashboard_exception_handling(client, app, monkeypatch):
    """Verifica que dashboard captura excepciones, registra auditoría de fallo, flashea mensaje y redirige a landing."""
    from app.models import get_session_factory, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash

    user_pw = generate_password_hash("SecureUserDash1!")
    user = crear_usuario(
        nombre="Dashboard Test User",
        apellido="User",
        email="dash_test_exception@example.com",
        prefijo_pais="+1",
        telefono="1234567890",
        password_hash=user_pw,
    )
    user_id = user['user_id']

    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = "dash_test_exception@example.com"
        sess['nombre'] = "Dashboard Test User"
        sess['role'] = "user"
        sess['_pw_hash'] = hashlib.sha256(user_pw.encode('utf-8')).hexdigest()

    def mock_obtener_juegos_error(uid):
        raise RuntimeError("Simulated Database Error")

    monkeypatch.setattr('app.routes.obtener_juegos_por_usuario', mock_obtener_juegos_error)

    response = client.get('/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert response.location.endswith('/') or response.location.endswith('/landing')

    with client.session_transaction() as sess:
        flashes = sess.get('_flashes', [])
        assert len(flashes) > 0
        assert flashes[0][1] == 'No se pudo cargar el panel de control.'

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user_id,
                AuditLog.action == 'VIEW_DASHBOARD',
                AuditLog.resource == 'dashboard',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'view_dashboard'
        assert 'Simulated Database Error' in log.details.get('error', '')
