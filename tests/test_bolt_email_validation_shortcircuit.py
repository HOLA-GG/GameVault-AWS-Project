"""Pruebas de optimización para la validación short-circuit de email."""

from app.models import validar_email


def test_validar_email_short_circuit_missing_at():
    """Valida que correos sin @ fallen de inmediato vía short-circuit."""
    assert validar_email("usergmail.com") is False
    assert validar_email("admin") is False
    assert validar_email("invalid_email_string_123") is False


def test_validar_email_valid_addresses():
    """Valida que correos válidos sigan funcionando correctamente."""
    assert validar_email("user@example.com") is True
    assert validar_email("john.doe@sub.domain.co") is True
    assert validar_email("alex_99+tag@gmail.org") is True


def test_validar_email_consecutive_dots_rejection():
    """Valida que correos con puntos consecutivos se rechacen."""
    assert validar_email("user..name@example.com") is False
    assert validar_email("user@domain..com") is False


def test_validar_email_invalid_types_and_bounds():
    """Valida que entradas no válidas, nulas o con longitud excesiva se rechacen."""
    assert validar_email(None) is False
    assert validar_email("") is False
    assert validar_email(12345) is False
    assert validar_email("a" * 256) is False
