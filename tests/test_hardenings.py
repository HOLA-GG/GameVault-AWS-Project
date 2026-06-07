import pytest
from app.models import exportar_logs_csv

def test_csv_injection_hardening_with_whitespace():
    """Verifica que la protección contra CSV Injection maneje espacios en blanco al inicio."""
    logs = [
        {
            'audit_id': '1',
            'user_id': 'user1',
            'action': " =cmd|' /c calc'!A0",  # Payload with leading space
            'resource': 'games',
            'timestamp': '2023-01-01T00:00:00',
            'ip_address': '127.0.0.1',
            'status': 'SUCCESS',
            'details': {'note': 'normal note'}
        },
        {
            'audit_id': '2',
            'user_id': 'user2',
            'action': 'UPDATE_GAME',
            'resource': '  @games', # Payload with leading spaces
            'timestamp': '2023-01-01T00:00:01',
            'ip_address': '127.0.0.1',
            'status': 'SUCCESS',
            'details': {'payload': 'normal'}
        }
    ]

    csv_output = exportar_logs_csv(logs)
    lines = csv_output.splitlines()

    # Check action column for the first log entry
    row1 = lines[1].split(',')
    # action is field 2
    assert row1[2].startswith("' ")
    assert '=cmd' in row1[2]

    # Check resource column for the second log entry
    row2 = lines[2].split(',')
    # resource is field 3
    assert row2[3].startswith("'  @")
