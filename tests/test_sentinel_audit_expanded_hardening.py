import pytest
from app.models import redact_sensitive_details

def test_redact_expanded_keywords():
    """Verifica que los nuevos patrones de PII y financieros sean redactados."""
    sensitive_data = {
        "credit_card": "1234-5678-9012-3456",
        "cvv": "123",
        "ssn": "999-00-1111",
        "dni": "12345678X",
        "iban": "ES00112233445566778899",
        "passport_number": "PA123456",
        "tax_id": "ABC123456789",
        "account_number": "000111222333",
        "nested": {
            "cvc": "999"
        },
        "list_of_sensitive": [
            {"card": "Visa"},
            {"ssn": "000-00-0000"}
        ]
    }

    redacted = redact_sensitive_details(sensitive_data)

    assert redacted["credit_card"] == "[REDACTED]"
    assert redacted["cvv"] == "[REDACTED]"
    assert redacted["ssn"] == "[REDACTED]"
    assert redacted["dni"] == "[REDACTED]"
    assert redacted["iban"] == "[REDACTED]"
    assert redacted["passport_number"] == "[REDACTED]"
    assert redacted["tax_id"] == "[REDACTED]"
    assert redacted["account_number"] == "[REDACTED]"
    assert redacted["nested"]["cvc"] == "[REDACTED]"
    assert redacted["list_of_sensitive"][0]["card"] == "[REDACTED]"
    assert redacted["list_of_sensitive"][1]["ssn"] == "[REDACTED]"

def test_audit_detail_truncation():
    """Verifica que strings excesivamente largos sean truncados."""
    long_string = "A" * 2000
    details = {
        "user_input": long_string,
        "nested": {
            "large_payload": "B" * 1500
        }
    }

    redacted = redact_sensitive_details(details)

    assert len(redacted["user_input"]) == 1024
    assert redacted["user_input"] == "A" * 1024
    assert len(redacted["nested"]["large_payload"]) == 1024
    assert redacted["nested"]["large_payload"] == "B" * 1024

def test_redact_preserves_short_strings():
    """Verifica que los strings normales no se vean afectados si no son sensibles."""
    normal_data = {
        "username": "jules",
        "action": "LOGIN",
        "comment": "All good"
    }

    redacted = redact_sensitive_details(normal_data)

    assert redacted["username"] == "jules"
    assert redacted["action"] == "LOGIN"
    assert redacted["comment"] == "All good"
