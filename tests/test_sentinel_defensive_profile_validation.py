"""Tests para verificar la resistencia defensiva de funciones de actualización de perfil."""

import pytest
from app import create_app
import importlib
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def test_app(monkeypatch):
    db_path = PROJECT_ROOT / 'gamevault_test_defensive_profile.db'
    if db_path.exists():
        try:
            db_path.unlink()
        except OSError:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_path}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')
    monkeypatch.setenv('WTF_CSRF_ENABLED', 'false')

    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    app_module = importlib.import_module('app')
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


def test_actualizar_usuario_nombre_defensive_types(test_app):
    """Verifica que actualizar_usuario_nombre maneje tipos no string (None, int, etc.) de forma segura."""
    from app.models import actualizar_usuario_nombre, crear_usuario, obtener_usuario_por_id

    with test_app.app_context():
        user = crear_usuario("Test User", "", "test_nombre_defensive@example.com", "", "", "Password123!")
        user_id = user["user_id"]

        # Test None
        res_none = actualizar_usuario_nombre(user_id, None)
        assert res_none["success"] is True
        u_updated = obtener_usuario_por_id(user_id)
        assert u_updated["nombre"] == ""

        # Test int
        res_int = actualizar_usuario_nombre(user_id, 12345)
        assert res_int["success"] is True
        u_updated = obtener_usuario_por_id(user_id)
        assert u_updated["nombre"] == "12345"

        # Test oversized string
        res_long = actualizar_usuario_nombre(user_id, "A" * 200)
        assert res_long["success"] is True
        u_updated = obtener_usuario_por_id(user_id)
        assert len(u_updated["nombre"]) == 120


def test_actualizar_usuario_perfil_defensive_types(test_app):
    """Verifica que actualizar_usuario_perfil maneje tipos no string y trunca strings largos en los campos de cambios."""
    from app.models import actualizar_usuario_perfil, crear_usuario, obtener_usuario_por_id

    with test_app.app_context():
        user = crear_usuario("Test User Profile", "", "test_perfil_defensive@example.com", "", "", "Password123!")
        user_id = user["user_id"]

        cambios_non_string = {
            "nombre": 9999,
            "apellido": None,
            "prefijo_pais": 52,
            "telefono": 123456789012345678901234567890,
            "collection_visibility": 123,
        }

        res = actualizar_usuario_perfil(user_id, cambios_non_string)
        assert res["success"] is True

        u = obtener_usuario_por_id(user_id)
        assert u["nombre"] == "9999"
        assert u["apellido"] == ""
        assert u["prefijo_pais"] == "52"
        assert u["telefono"] == "12345678901234567890"  # Truncated to max 20 chars
        assert u["collection_visibility"] == "private"  # Non 'public' defaults to 'private'
