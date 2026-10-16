import sys
from unittest.mock import patch


def test_eliminar_juego_database_exception_handling():
    import app.models
    with patch("app.models.get_session_factory", side_effect=Exception("Simulated database failure during deletion")):
        res = sys.modules["app.models"].eliminar_juego("user-123", "game-123")
        assert res["success"] is False
        assert res["juego"] is None
        assert res["error"] == "Error al eliminar juego"


def test_actualizar_juego_database_exception_handling():
    import app.models
    with patch("app.models.get_session_factory", side_effect=Exception("Simulated database failure during update")):
        res = sys.modules["app.models"].actualizar_juego("user-123", "game-123", {"titulo": "Updated Title"})
        assert res["success"] is False
        assert res["juego"] is None
        assert res["error"] == "Error al actualizar juego"
