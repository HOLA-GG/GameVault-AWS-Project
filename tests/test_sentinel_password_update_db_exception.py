import sys
from unittest.mock import patch


def test_actualizar_password_usuario_database_exception_handling():
    import app.models
    with patch("app.models.get_session_factory", side_effect=Exception("Simulated database failure during password update")):
        res = sys.modules["app.models"].actualizar_password_usuario("user-123", "scrypt:32768:8:1$dummyhash")
        assert res["success"] is False
        assert res["error"] == "Error al actualizar contraseña"
