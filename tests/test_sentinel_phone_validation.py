"""Unit tests verifying phone number validation logic and defensive handling."""

from app.models import validar_telefono


def test_validar_telefono_valid_cases():
    """Verify standard valid phone numbers with and without leading/trailing whitespace."""
    assert validar_telefono("1234567") is True
    assert validar_telefono("5551234567") is True
    assert validar_telefono("  5551234567  ") is True
    assert validar_telefono("\t3001234567\n") is True
    assert validar_telefono("12345678901234567890") is True


def test_validar_telefono_invalid_cases():
    """Verify non-digits, out-of-bound lengths, and non-string inputs are rejected."""
    # Too short (< 7 digits)
    assert validar_telefono("123456") is False
    assert validar_telefono(" 123456 ") is False

    # Too long (> 20 digits)
    assert validar_telefono("123456789012345678901") is False

    # Non-digit characters
    assert validar_telefono("+12345678") is False
    assert validar_telefono("123-456-7890") is False
    assert validar_telefono("phone123456") is False

    # Empty, None, non-string types
    assert validar_telefono("") is False
    assert validar_telefono("   ") is False
    assert validar_telefono(None) is False
    assert validar_telefono(123456789) is False
    assert validar_telefono(["5551234567"]) is False
