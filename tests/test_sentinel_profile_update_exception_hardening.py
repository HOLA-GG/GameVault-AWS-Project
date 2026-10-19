"""Pruebas de hardening contra excepciones no controladas en actualizar_usuario_perfil."""

import sys
from unittest.mock import patch


def test_actualizar_usuario_perfil_database_exception_handling():
    import app.models
    with patch("app.models.get_session_factory", side_effect=Exception("Database connection failure")):
        res = sys.modules["app.models"].actualizar_usuario_perfil("user-123", {"nombre": "Nuevo Nombre"})
        assert res["success"] is False
        assert res["error"] == "Error al actualizar perfil"
