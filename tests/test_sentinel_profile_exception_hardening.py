"""Pruebas de hardening contra excepciones no controladas en la ruta de perfil /perfil."""

import sys
import importlib
from pathlib import Path
from unittest.mock import patch
import pytest
from werkzeug.security import generate_password_hash

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def test_app(monkeypatch):
    db_path = PROJECT_ROOT / "gamevault_test_profile_exception.db"
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    monkeypatch.setenv("RATELIMIT_ENABLED", "0")
    monkeypatch.setenv("WTF_CSRF_ENABLED", "false")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            sys.modules.pop(module_name)

    app_module = importlib.import_module("app")
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })

    yield flask_app

    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass


def test_profile_route_exception_handling(test_app):
    """Verifica que excepciones inesperadas en /perfil se capturen, registren un audit log FAILED y redirijan de forma segura."""
    models = sys.modules["app.models"]

    client = test_app.test_client()

    with test_app.app_context():
        pw_hash = generate_password_hash("Pass1234!")
        user = models.crear_usuario("User Exception", "", "profile_exc@example.com", "+56", "912345678", pw_hash)
        user_id = user["user_id"]

    import hashlib
    pw_hash_gen = hashlib.sha256(pw_hash.encode("utf-8")).hexdigest()

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["email"] = "profile_exc@example.com"
        sess["nombre"] = "User Exception"
        sess["role"] = "user"
        sess["_pw_hash"] = pw_hash_gen
        sess["_user_agent"] = "python-test"

    with patch("app.routes.obtener_metricas_coleccion", side_effect=Exception("Unexpected database glitch")):
        response = client.get("/perfil", headers={"User-Agent": "python-test"}, follow_redirects=True)
        assert response.status_code == 200
        assert "No se pudo procesar la solicitud de perfil." in response.get_data(as_text=True)

    with test_app.app_context():
        logs = models.obtener_todos_logs({"user_id": user_id, "status": "FAILED"})
        failed_profile_logs = [l for l in logs if l.get("action") == "UPDATE_PROFILE"]
        assert len(failed_profile_logs) >= 1
        assert failed_profile_logs[0]["status"] == "FAILED"
        assert failed_profile_logs[0]["details"].get("reason") == "exception_raised"
