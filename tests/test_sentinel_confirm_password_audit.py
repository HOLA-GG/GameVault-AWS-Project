import os
import sys
from pathlib import Path
import pytest
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_confirm_audit.db'
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


def test_password_change_incorrect_current_password_with_long_confirm_audited(client, app):
    """Verifica que cambiar contraseña con contraseña actual incorrecta y confirm_password larga audite FAILED."""
    from app.models import crear_usuario, obtener_logs_por_usuario

    email = "test_confirm_audit@example.com"
    password_hash = generate_password_hash("ValidPass123")
    user = crear_usuario("TestUser", "Apellido", email, "+52", "1234567890", password_hash)
    user_id = user["user_id"]

    # Iniciar sesión con hash matching
    pw_hash = generate_password_hash("ValidPass123")
    import hashlib
    pw_sha256 = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # Actualizar hash en DB para que coincida con la sesión
    from app.models import actualizar_password_usuario
    actualizar_password_usuario(user_id, pw_hash)

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["email"] = email
        sess["nombre"] = "TestUser"
        sess["role"] = "user"
        sess["_pw_hash"] = pw_sha256
        sess["_user_agent"] = "python-test"

    # Intentar cambiar contraseña con current_password incorrecta y confirm_password > 128
    response = client.post(
        "/perfil",
        data={
            "form_name": "password",
            "current_password": "WrongPassword123",
            "password": "NewPassword123",
            "confirm_password": "A" * 200,
        },
        headers={"User-Agent": "python-test"},
        follow_redirects=True,
    )

    assert response.status_code == 200

    # Verificar que se registró el log de auditoría FAILED con reason='incorrect_current_password'
    logs = obtener_logs_por_usuario(user_id)
    failed_logs = [
        log for log in logs
        if log["action"] == "CHANGE_PASSWORD" and log["status"] == "FAILED"
    ]
    assert len(failed_logs) > 0, "Debe existir un log FAILED para CHANGE_PASSWORD"
    assert failed_logs[0]["details"].get("reason") == "incorrect_current_password"
