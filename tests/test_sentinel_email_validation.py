"""Unit tests verifying email validation logic and security defenses."""

from app.models import validar_email


def test_validar_email_valid_cases():
    """Verify standard valid email formats."""
    assert validar_email("user@example.com") is True
    assert validar_email("john.doe@sub.domain.co") is True
    assert validar_email("alex_99+tag@gmail.org") is True


def test_validar_email_consecutive_dots_rejection():
    """Verify emails with consecutive dots are rejected."""
    assert validar_email("user..name@example.com") is False
    assert validar_email("user@domain..com") is False
    assert validar_email("..user@example.com") is False
    assert validar_email("user..@example.com") is False


def test_validar_email_invalid_types_and_lengths():
    """Verify non-string, empty, and oversized inputs are handled defensively."""
    assert validar_email(None) is False
    assert validar_email("") is False
    assert validar_email(12345) is False
    assert validar_email(["user@example.com"]) is False

    oversized_email = "a" * 250 + "@example.com"
    assert validar_email(oversized_email) is False
