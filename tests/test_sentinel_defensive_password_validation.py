"""Pruebas de robustez para validar_password, validar_email y validar_telefono frente a tipos de datos no válidos."""

from app.models import validar_email, validar_password, validar_telefono


def test_validar_password_non_string_types():
    assert validar_password(None) is False
    assert validar_password(12345678) is False
    assert validar_password(['Password123']) is False
    assert validar_password({'password': 'Password123'}) is False


def test_validar_password_non_string_metadata():
    valid_pw = "SecurePass123!"
    assert validar_password(valid_pw, email=None, nombre=None, apellido=None, telefono=None) is True
    assert validar_password(valid_pw, email=123, nombre=['John'], apellido={'a': 'b'}, telefono=True) is True


def test_validar_email_non_string_types():
    assert validar_email(None) is False
    assert validar_email(12345) is False
    assert validar_email(['test@example.com']) is False


def test_validar_telefono_non_string_types():
    assert validar_telefono(None) is False
    assert validar_telefono(123456789) is False
    assert validar_telefono(['123456789']) is False
