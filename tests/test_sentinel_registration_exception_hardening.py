import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_registration_exception_hardening.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
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


def test_registration_exception_handling(client, monkeypatch):
    """Verifies that unexpected runtime or database exceptions during user registration
    are gracefully caught, logged as a FAILED audit trail entry, and safely redirected."""
    from app.models import get_session_factory, AuditLog, select

    import app.routes

    def mock_obtener_usuario_por_email(email, **kwargs):
        raise RuntimeError("Database connection failure during registration existence lookup")

    monkeypatch.setattr(app.routes, 'obtener_usuario_por_email', mock_obtener_usuario_por_email)

    response = client.post(
        '/registro',
        data={
            'nombre': 'TestUser',
            'email': 'exception_test@example.com',
            'password': 'ValidPassword123!',
            'confirm_password': 'ValidPassword123!',
        },
        headers={'User-Agent': 'python-test'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'No se pudo procesar el registro.' in response.data

    session_factory = get_session_factory()
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == 'REGISTER',
                AuditLog.status == 'FAILED'
            ).order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'
        assert 'Database connection failure' in log.details.get('error', '')
