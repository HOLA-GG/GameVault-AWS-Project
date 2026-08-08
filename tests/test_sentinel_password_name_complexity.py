import pytest
from app.models import validar_password

def test_validar_password_with_name():
    """Verifica que la contraseña no pueda contener el nombre del usuario si este tiene >= 4 caracteres."""
    # Contraseña fuerte válida
    assert validar_password("StrongPass123!", email="test@example.com", nombre="Juan") is True

    # Contraseña que contiene el nombre del usuario (debe ser bloqueada)
    assert validar_password("JuanPass123!", email="test@example.com", nombre="Juan") is False

    # El chequeo del nombre debe ser insensible a mayúsculas/minúsculas
    assert validar_password("juanPass123!", email="test@example.com", nombre="Juan") is False
    assert validar_password("JUANPass123!", email="test@example.com", nombre="juan") is False

    # Nombres de menos de 4 caracteres no deben causar bloqueos falsos
    assert validar_password("AnaPass123!", email="test@example.com", nombre="Ana") is True

    # Chequeo sin nombre provisto debe seguir funcionando normalmente
    assert validar_password("StrongPass123!", email="test@example.com") is True
