"""Tests de seguridad para la validación defensiva de IDs (is_valid_id)."""

from app.routes import is_valid_id


def test_is_valid_id_valid_cases():
    """Verifica que IDs válidos (UUIDs, alfanuméricos con guiones) sean aceptados."""
    assert is_valid_id("usr-12345") is True
    assert is_valid_id("550e8400-e29b-41d4-a716-446655440000") is True
    assert is_valid_id("a_b_c_123") is True


def test_is_valid_id_non_string_inputs():
    """Verifica que is_valid_id retorne False de forma segura para tipos no-cadena."""
    assert is_valid_id(None) is False
    assert is_valid_id(12345) is False
    assert is_valid_id(["usr-12345"]) is False
    assert is_valid_id({"id": "usr-12345"}) is False
    assert is_valid_id(True) is False


def test_is_valid_id_invalid_and_oversized_strings():
    """Verifica que cadenas vacías, con caracteres inválidos o de longitud > 36 sean rechazadas."""
    assert is_valid_id("") is False
    assert is_valid_id("a" * 37) is False
    assert is_valid_id("usr-12345; DROP TABLE users;") is False
    assert is_valid_id("<script>alert(1)</script>") is False
    assert is_valid_id("usr-12345\x00") is False
