import pytest
from app.models import validar_password, redact_sensitive_details

def test_new_weak_passwords_rejected():
    """Verify that newly added common weak passwords are rejected."""
    weak_passwords = [
        'password123', 'admin123', 'admin1234', 'admin12345', 'gamer123',
        'videogames123', 'qwerty123', '12345678a', 'password1234', 'welcome123',
        'PASSWORD123', 'Admin123'  # Test case-insensitivity
    ]

    for pwd in weak_passwords:
        assert validar_password(pwd) is False, f"Password {pwd} should be rejected"

def test_valid_passwords_still_accepted():
    """Verify that valid complex passwords are still accepted."""
    valid_passwords = [
        'ComplexPass123!',
        'SecureGamer2024',
        'VaultGuard_99'
    ]

    for pwd in valid_passwords:
        assert validar_password(pwd) is True, f"Password {pwd} should be accepted"

def test_new_sensitive_patterns_redacted():
    """Verify that new sensitive patterns are correctly redacted."""
    sensitive_data = {
        'recovery_token': 'secret123',
        'security_answer': 'my_dog',
        'identity_number': 'ID-456',
        'national_id': 'NAT-789',
        'personal_id': 'PER-000',
        'tarjeta_credito': '1234-5678',
        'clave_acceso': 'abc-123',
        'cuenta_bancaria': 'IBAN-XYZ',
        'identidad_digital': 'DID-111',
        'expiry_date': '12/26',
        'expiration_time': '2026-01-01',
        'safe_field': 'hello world'
    }

    redacted = redact_sensitive_details(sensitive_data)

    assert redacted['recovery_token'] == '[REDACTED]'
    assert redacted['security_answer'] == '[REDACTED]'
    assert redacted['identity_number'] == '[REDACTED]'
    assert redacted['national_id'] == '[REDACTED]'
    assert redacted['personal_id'] == '[REDACTED]'
    assert redacted['tarjeta_credito'] == '[REDACTED]'
    assert redacted['clave_acceso'] == '[REDACTED]'
    assert redacted['cuenta_bancaria'] == '[REDACTED]'
    assert redacted['identidad_digital'] == '[REDACTED]'
    assert redacted['expiry_date'] == '[REDACTED]'
    assert redacted['expiration_time'] == '[REDACTED]'
    assert redacted['safe_field'] == 'hello world'
