"""
tests/test_bolt_csv_writer_positional.py - Tests verifying positional csv.writer optimization in exportar_logs_csv.
"""

import io
import csv
from app.models import exportar_logs_csv, _sanitize_csv_val


def test_exportar_logs_csv_positional_writer_matches_expected_format():
    """Verify exportar_logs_csv produces standard CSV headers and correctly ordered rows."""
    logs = [
        {
            'audit_id': 'log-001',
            'user_id': 'usr-001',
            'action': 'LOGIN',
            'resource': 'auth',
            'timestamp': '2026-11-01T10:00:00+00:00',
            'ip_address': '192.168.1.1',
            'status': 'SUCCESS',
            'details': {'ip': '192.168.1.1'},
        },
        {
            'audit_id': 'log-002',
            'user_id': 'usr-002',
            'action': 'UPDATE_PROFILE',
            'resource': 'users',
            'timestamp': '2026-11-01T10:05:00+00:00',
            'ip_address': '10.0.0.1',
            'status': 'SUCCESS',
            'details': None,
        },
        {
            'audit_id': 'log-003',
            'user_id': '=SUM(1,2)',  # CSV injection candidate
            'action': 'LOGOUT',
            'resource': 'auth',
            'timestamp': '2026-11-01T10:10:00+00:00',
            'ip_address': '127.0.0.1',
            'status': 'SUCCESS',
            'details': '',
        },
    ]

    csv_output = exportar_logs_csv(logs)
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)

    # Verify header
    expected_header = ['audit_id', 'user_id', 'action', 'resource', 'timestamp', 'ip_address', 'status', 'details']
    assert rows[0] == expected_header

    # Row 1
    assert rows[1] == [
        'log-001',
        'usr-001',
        'LOGIN',
        'auth',
        '2026-11-01T10:00:00+00:00',
        '192.168.1.1',
        'SUCCESS',
        "{'ip': '192.168.1.1'}",
    ]

    # Row 2 (details is None, should default to '{}')
    assert rows[2] == [
        'log-002',
        'usr-002',
        'UPDATE_PROFILE',
        'users',
        '2026-11-01T10:05:00+00:00',
        '10.0.0.1',
        'SUCCESS',
        '{}',
    ]

    # Row 3 (sanitized formula prefix and empty details string)
    assert rows[3][1] == "'=SUM(1,2)"
    assert rows[3][7] == '{}'


def test_exportar_logs_csv_sparse_records_fallback():
    """Verify fallback path handles partial/sparse dictionary entries missing keys."""
    sparse_logs = [
        {
            'audit_id': 'log-sparse-1',
            'action': 'ADMIN_ACTION',
        },
        {
            'user_id': 'usr-only',
        },
    ]

    csv_output = exportar_logs_csv(sparse_logs)
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)

    assert rows[0] == ['audit_id', 'user_id', 'action', 'resource', 'timestamp', 'ip_address', 'status', 'details']
    # Sparse 1
    assert rows[1] == ['log-sparse-1', '', 'ADMIN_ACTION', '', '', '', '', '{}']
    # Sparse 2
    assert rows[2] == ['', 'usr-only', '', '', '', '', '', '{}']


def test_exportar_logs_csv_empty_list():
    """Verify empty logs input returns only header."""
    csv_output = exportar_logs_csv([])
    reader = csv.reader(io.StringIO(csv_output))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0] == ['audit_id', 'user_id', 'action', 'resource', 'timestamp', 'ip_address', 'status', 'details']
