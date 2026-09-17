import os
import sys
from pathlib import Path
import pytest
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_registration_audit.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    from app import create_app
    flask_app = create_app()
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


def test_registration_failure_audit_logged(client, app):
    """Verifies that when crear_usuario returns None during registration,
    a REGISTER audit log entry with status FAILED and reason account_creation_failed is created."""
    from app.models import obtener_todos_logs

    email = "test_reg_fail@example.com"

    with patch("app.routes.crear_usuario", return_value=None):
        response = client.post(
            "/registro",
            data={
                "nombre": "TestUser",
                "email": email,
                "password": "ValidPassword123!",
                "confirm_password": "ValidPassword123!",
            },
            headers={"User-Agent": "python-test"},
            follow_redirects=True,
        )

    assert response.status_code == 200

    logs = obtener_todos_logs({"action": "REGISTER", "status": "FAILED"})
    matching_logs = [
        log for log in logs
        if log["details"].get("email") == email and log["details"].get("reason") == "account_creation_failed"
    ]
    assert len(matching_logs) == 1, "Debe registrarse un log FAILED de REGISTER con reason 'account_creation_failed'"
