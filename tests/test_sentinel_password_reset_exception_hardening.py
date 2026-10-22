import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_password_reset_exception_hardening.db'
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


def test_forgot_password_exception_handling(client, monkeypatch):
    """Verifies that unexpected database/runtime exceptions in forgot_password log a FAILED audit trail and redirect safely."""
    from app.models import get_session_factory, AuditLog, select

    import app.routes
    def mock_obtener_usuario(email, **kwargs):
        raise RuntimeError("Database connectivity lost during user recovery lookup")

    monkeypatch.setattr(app.routes, 'obtener_usuario_por_email', mock_obtener_usuario)

    response = client.post('/forgot-password', data={'email': 'recovery_test@example.com'}, follow_redirects=True)

    assert response.status_code == 200
    assert b'No se pudo procesar la solicitud de recuperaci' in response.data

    session_factory = get_session_factory()
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == 'PASSWORD_RESET_REQUEST',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'
        assert 'Database connectivity lost' in log.details.get('error', '')


def test_forgot_password_manual_exception_handling(client, monkeypatch):
    """Verifies that unexpected database/runtime exceptions in forgot_password_manual log a FAILED audit trail and redirect safely."""
    from app.models import get_session_factory, AuditLog, select

    import app.routes
    def mock_obtener_usuario(email, **kwargs):
        raise RuntimeError("Database connectivity lost during manual recovery lookup")

    monkeypatch.setattr(app.routes, 'obtener_usuario_por_email', mock_obtener_usuario)

    response = client.post('/forgot-password/manual', data={'email': 'recovery_manual@example.com', 'telefono': '1234567890'}, follow_redirects=True)

    assert response.status_code == 200
    assert b'No se pudo procesar la solicitud de recuperaci' in response.data

    session_factory = get_session_factory()
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == 'PASSWORD_RESET_REQUEST',
                AuditLog.status == 'FAILED'
            ).order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'
        assert 'Database connectivity lost' in log.details.get('error', '')
