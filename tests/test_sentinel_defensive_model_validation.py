"""Test suite for Sentinel defensive validation on database model helper functions."""

import pytest
from app.models import (
    obtener_juego_por_id,
    obtener_usuario_por_email,
    obtener_usuario_por_id,
    eliminar_usuario,
    actualizar_usuario_perfil,
    actualizar_password_usuario,
)


def test_obtener_juego_por_id_defensive():
    """Verify defensive handling of invalid parameters in obtener_juego_por_id."""
    assert obtener_juego_por_id(None, "game123") is None
    assert obtener_juego_por_id(12345, "game123") is None
    assert obtener_juego_por_id("user123", None) is None
    assert obtener_juego_por_id("user123", ["game123"]) is None
    assert obtener_juego_por_id("a" * 37, "game123") is None
    assert obtener_juego_por_id("user123", "b" * 37) is None


def test_obtener_usuario_por_email_defensive():
    """Verify defensive handling of invalid parameters in obtener_usuario_por_email."""
    assert obtener_usuario_por_email(None) is None
    assert obtener_usuario_por_email(12345) is None
    assert obtener_usuario_por_email(["test@example.com"]) is None
    assert obtener_usuario_por_email("a" * 256 + "@example.com") is None


def test_obtener_usuario_por_id_defensive():
    """Verify defensive handling of invalid parameters in obtener_usuario_por_id."""
    assert obtener_usuario_por_id(None) is None
    assert obtener_usuario_por_id(999) is None
    assert obtener_usuario_por_id({"id": "123"}) is None
    assert obtener_usuario_por_id("u" * 37) is None


def test_eliminar_usuario_defensive():
    """Verify defensive handling of invalid parameters in eliminar_usuario."""
    res_none = eliminar_usuario(None)
    assert res_none["success"] is False
    assert res_none["error"] == "Usuario no encontrado"

    res_int = eliminar_usuario(123)
    assert res_int["success"] is False

    res_long = eliminar_usuario("x" * 37)
    assert res_long["success"] is False


def test_actualizar_usuario_perfil_defensive():
    """Verify defensive handling of invalid parameters in actualizar_usuario_perfil."""
    res_none_id = actualizar_usuario_perfil(None, {"nombre": "Test"})
    assert res_none_id["success"] is False
    assert res_none_id["error"] == "Usuario no encontrado"

    res_invalid_cambios = actualizar_usuario_perfil("user123", None)
    assert res_invalid_cambios["success"] is False
    assert res_invalid_cambios["error"] == "Datos de perfil inválidos"


def test_actualizar_password_usuario_defensive():
    """Verify defensive handling of invalid parameters in actualizar_password_usuario."""
    res_none_id = actualizar_password_usuario(None, "scrypt:32768:8:1$hash")
    assert res_none_id["success"] is False
    assert res_none_id["error"] == "Usuario no encontrado"

    res_none_hash = actualizar_password_usuario("user123", None)
    assert res_none_hash["success"] is False
    assert res_none_hash["error"] == "Hash de contraseña inválido"

    res_long_hash = actualizar_password_usuario("user123", "h" * 256)
    assert res_long_hash["success"] is False
