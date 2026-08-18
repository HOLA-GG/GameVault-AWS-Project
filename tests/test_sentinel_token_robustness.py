"""Tests de robustez para funciones de tokens de recuperación contra tipos inválidos y nulos."""

import pytest
from app.models import hash_token, obtener_token_por_valor, validar_reset_token, usar_token


def test_hash_token_robustness():
    """Verifica que hash_token maneja None, cadenas vacías y tipos no-cadena sin fallar."""
    # None input
    assert isinstance(hash_token(None), str)
    assert len(hash_token(None)) == 64

    # Empty string input
    assert hash_token("") == hash_token(None)

    # Integer input
    assert isinstance(hash_token(12345), str)


def test_obtener_token_por_valor_robustness():
    """Verifica que obtener_token_por_valor retorna lista vacía para inputs inválidos."""
    assert obtener_token_por_valor(None) == []
    assert obtener_token_por_valor("") == []
    assert obtener_token_por_valor(12345) == []
    assert obtener_token_por_valor({"token": "abc"}) == []
    assert obtener_token_por_valor(["token_a"]) == []


def test_validar_reset_token_robustness():
    """Verifica que validar_reset_token responde con diccionario de error para inputs inválidos."""
    for invalid_token in (None, "", 12345, {"token": "xyz"}, ["abc"]):
        res = validar_reset_token(invalid_token)
        assert res["valid"] is False
        assert res["user_id"] is None
        assert "error" in res


def test_usar_token_robustness():
    """Verifica que usar_token responde con diccionario de error para inputs inválidos."""
    for invalid_token in (None, "", 12345, {"token": "xyz"}, ["abc"]):
        res = usar_token(invalid_token)
        assert res["success"] is False
        assert "error" in res
