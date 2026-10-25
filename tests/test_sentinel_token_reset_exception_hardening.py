import os
import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_token_reset_exception_hardening.db'
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


def test_verify_token_exception_handling(client, monkeypatch):
    from app.models import get_session_factory, AuditLog, select
    import app.routes

    def mock_validar_token(token):
        raise RuntimeError("Database connectivity lost during token validation")

    monkeypatch.setattr(app.routes, 'validar_reset_token', mock_validar_token)

    response = client.post('/verify-token', data={'token': 'valid-looking-token-12345'}, follow_redirects=True)

    assert response.status_code == 200
    assert 'No se pudo procesar la validación del token.' in response.get_data(as_text=True)

    session_factory = get_session_factory()
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == 'TOKEN_VALIDATION_FAILED',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'
        assert log.details.get('context') == 'verify_token'
        assert 'Database connectivity lost' in log.details.get('error', '')


def test_reset_password_with_email_exception_handling(client, monkeypatch):
    from app.models import get_session_factory, AuditLog, select
    import app.routes

    def mock_validar_token(token):
        raise RuntimeError("Database connectivity lost during reset token validation")

    monkeypatch.setattr(app.routes, 'validar_reset_token', mock_validar_token)

    response = client.post('/reset-password/valid-looking-token-12345', data={
        'password': 'NewPassword123!',
        'confirm_password': 'NewPassword123!'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert 'No se pudo procesar el restablecimiento de la contraseña.' in response.get_data(as_text=True)

    session_factory = get_session_factory()
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.action == 'TOKEN_VALIDATION_FAILED',
                AuditLog.status == 'FAILED'
            ).order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'
        assert log.details.get('context') == 'reset_password'
        assert 'Database connectivity lost' in log.details.get('error', '')
