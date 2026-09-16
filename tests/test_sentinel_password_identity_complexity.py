import pytest
from app.models import validar_password

def test_validar_password_with_apellido():
    """Verifica que la contraseña no pueda contener el apellido del usuario si este tiene >= 4 caracteres."""
    # Contraseña fuerte válida
    assert validar_password("StrongPass123!", email="test@example.com", nombre="Juan", apellido="Perez") is True

    # Contraseña que contiene el apellido (debe ser bloqueada)
    assert validar_password("PerezPass123!", email="test@example.com", nombre="Juan", apellido="Perez") is False

    # El chequeo del apellido debe ser insensible a mayúsculas/minúsculas
    assert validar_password("perezPass123!", email="test@example.com", nombre="Juan", apellido="Perez") is False
    assert validar_password("PEREZPass123!", email="test@example.com", nombre="Juan", apellido="perez") is False

    # Apellidos de menos de 4 caracteres no deben causar bloqueos falsos
    assert validar_password("GilPass123!", email="test@example.com", nombre="Juan", apellido="Gil") is True

    # Chequeo sin apellido provisto debe seguir funcionando normalmente
    assert validar_password("StrongPass123!", email="test@example.com", nombre="Juan") is True


def test_validar_password_with_telefono():
    """Verifica que la contraseña no pueda contener el teléfono del usuario si este tiene >= 4 dígitos."""
    # Contraseña fuerte válida
    assert validar_password("StrongPass123!", email="test@example.com", nombre="Juan", telefono="5551234567") is True

    # Contraseña que contiene el teléfono (debe ser bloqueada)
    assert validar_password("Pass5551234567!", email="test@example.com", nombre="Juan", telefono="5551234567") is False

    # El chequeo del teléfono debe normalizar caracteres no numéricos
    assert validar_password("Pass5551234567!", email="test@example.com", nombre="Juan", telefono="555-123-4567") is False
    assert validar_password("Pass5551234567!", email="test@example.com", nombre="Juan", telefono="(555) 123-4567") is False

    # Teléfonos de menos de 4 dígitos no deben causar bloqueos falsos
    assert validar_password("Pass123!", email="test@example.com", nombre="Juan", telefono="123") is True

    # Chequeo sin teléfono provisto debe seguir funcionando normalmente
    assert validar_password("StrongPass123!", email="test@example.com", nombre="Juan") is True
