import pytest
from flask import Flask, g
from app.models import crear_log_audit, obtener_todos_logs, redact_sensitive_details, exportar_logs_csv

def test_new_sensitive_redaction():
    """Verify that new sensitive patterns are correctly redacted."""
    details = {
        'csrf_token': 'secret-csrf',
        'xsrf-header': 'secret-xsrf',
        'access_token': 'secret-access',
        'refresh_token': 'secret-refresh',
        'id_token': 'secret-id',
        'authorization': 'Bearer secret',
        'bearer': 'some-bearer-token',
        'nif': '12345678A',
        'nie': 'X1234567L',
        'curp': 'ABCD123456HDFRRR01',
        'safe_field': 'not-sensitive'
    }
    redacted = redact_sensitive_details(details)

    assert redacted['csrf_token'] == '[REDACTED]'
    assert redacted['xsrf-header'] == '[REDACTED]'
    assert redacted['access_token'] == '[REDACTED]'
    assert redacted['refresh_token'] == '[REDACTED]'
    assert redacted['id_token'] == '[REDACTED]'
    assert redacted['authorization'] == '[REDACTED]'
    assert redacted['bearer'] == '[REDACTED]'
    assert redacted['nif'] == '[REDACTED]'
    assert redacted['nie'] == '[REDACTED]'
    assert redacted['curp'] == '[REDACTED]'
    assert redacted['safe_field'] == 'not-sensitive'

def test_audit_request_id_injection():
    """Verify that request_id is automatically injected into audit logs within a request context."""
    app = Flask(__name__)
    with app.app_context():
        g.request_id = 'test-request-id-123'

        # Test creation
        result = crear_log_audit(
            user_id='test-user',
            action='TEST_ACTION',
            resource='test-resource',
            details={'foo': 'bar'}
        )
        assert result['success'] is True

        # Verify persistence and injection
        logs = obtener_todos_logs(limit=1)
        assert len(logs) > 0
        log = logs[0]
        assert log['details']['request_id'] == 'test-request-id-123'
        assert log['details']['foo'] == 'bar'

def test_csv_injection_backtick():
    """Verify that the backtick character is protected in CSV exports."""
    logs = [{
        'audit_id': '1',
        'user_id': 'u1',
        'action': 'A',
        'resource': 'R',
        'timestamp': '2025-01-01',
        'ip_address': '1.1.1.1',
        'status': 'SUCCESS',
        'details': {'title': '`=SUM(1,2)'}
    }]
    csv_content = exportar_logs_csv(logs)
    # The backtick should be prepended with a single quote if it starts the field
    # Wait, the logic is: val.lstrip().startswith(_RISKY_CSV_CHARS)
    # So if title is "`=SUM(1,2)", it should become "'`=SUM(1,2)"
    assert "'`=SUM(1,2)" in csv_content
