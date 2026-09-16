"""Prueba unitaria para verificar la optimización de redact_sensitive_details."""

import pytest
from app.models import redact_sensitive_details


def test_redact_sensitive_details_token_and_reset_url():
    # Verify reset password URL redaction
    data_reset = {'url': 'https://example.com/reset-password/secret123token'}
    redacted_reset = redact_sensitive_details(data_reset)
    assert redacted_reset['url'] == 'https://example.com/reset-password/[REDACTED]'

    # Verify token parameter redaction
    data_query = {'url': 'https://example.com/verify?token=secret123token&other=val'}
    redacted_query = redact_sensitive_details(data_query)
    assert redacted_query['url'] == 'https://example.com/verify?token=[REDACTED]&other=val'

    # Verify uppercase/mixed-case TOKEN parameter redaction
    data_upper = {'url': 'https://example.com/verify?TOKEN=secret123token'}
    redacted_upper = redact_sensitive_details(data_upper)
    assert redacted_upper['url'] == 'https://example.com/verify?TOKEN=[REDACTED]'


def test_redact_sensitive_details_normal_string():
    # Verify normal strings pass through without alteration or errors
    normal_data = {
        'action': 'CREATE_GAME',
        'resource': 'games',
        'details': {
            'title': 'Super Mario Bros',
            'platform': 'Nintendo',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'ip': '192.168.1.1',
        },
    }
    redacted = redact_sensitive_details(normal_data)
    assert redacted['action'] == 'CREATE_GAME'
    assert redacted['details']['title'] == 'Super Mario Bros'
    assert redacted['details']['platform'] == 'Nintendo'
