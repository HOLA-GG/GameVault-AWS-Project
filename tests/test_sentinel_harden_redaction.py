import pytest
from app.models import redact_sensitive_details

def test_expanded_redaction_patterns():
    """Verify that new PII and security keywords are redacted."""
    sensitive_data = {
        'telefono': '555-1234',
        'phone': '123-4567',
        'apikey': 'sk_live_12345',
        'pin': '1234',
        'direccion': 'Calle Falsa 123',
        'address': '123 Fake St',
        'birth': '1990-01-01',
        'nacimiento': '1990-01-01',
        'celular': '999-888',
        'mobile': '777-666',
        'safe_field': 'not sensitive'
    }

    redacted = redact_sensitive_details(sensitive_data)

    assert redacted['telefono'] == '[REDACTED]'
    assert redacted['phone'] == '[REDACTED]'
    assert redacted['apikey'] == '[REDACTED]'
    assert redacted['pin'] == '[REDACTED]'
    assert redacted['direccion'] == '[REDACTED]'
    assert redacted['address'] == '[REDACTED]'
    assert redacted['birth'] == '[REDACTED]'
    assert redacted['nacimiento'] == '[REDACTED]'
    assert redacted['celular'] == '[REDACTED]'
    assert redacted['mobile'] == '[REDACTED]'
    assert redacted['safe_field'] == 'not sensitive'

def test_redaction_recursion_depth():
    """Verify that deep nesting triggers the MAX_DEPTH_REACHED safety."""
    # Create a nested dictionary 11 levels deep
    deep_data = {}
    current = deep_data
    for _ in range(11):
        current['next'] = {}
        current = current['next']
    current['bottom'] = 'value'

    redacted = redact_sensitive_details(deep_data)

    # Check that at some point we get the depth limit marker
    # Level 0: {'next': {}}
    # ...
    # Level 10: {'next': {}} -> redact_sensitive_details(next, 11) -> [MAX_DEPTH_REACHED]

    curr = redacted
    for _ in range(10):
        curr = curr['next']

    assert curr['next'] == '[MAX_DEPTH_REACHED]'

def test_redaction_in_list():
    """Verify redaction still works within lists."""
    list_data = [
        {'password': 'secret'},
        {'safe': 'data'},
        ['nested', {'token': 'abc'}]
    ]

    redacted = redact_sensitive_details(list_data)

    assert redacted[0]['password'] == '[REDACTED]'
    assert redacted[1]['safe'] == 'data'
    assert redacted[2][1]['token'] == '[REDACTED]'
