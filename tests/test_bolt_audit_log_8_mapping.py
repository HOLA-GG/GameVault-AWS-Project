"""
tests/test_bolt_audit_log_8_mapping.py - Tests for fast-path 8-column audit log row mapping optimization.
"""

from app.models import _audit_log_row_to_dict, _fast_format_dt, MIN_DATE, _MIN_DATE_ISO


class MockAuditLogRow8:
    def __init__(self, data=None):
        base = {
            'audit_id': 'audit-123',
            'user_id': 'user-456',
            'action': 'ADMIN_ACTION',
            'resource': 'audit_logs',
            'timestamp': '2026-09-22T12:00:00+00:00',
            'ip_address': '192.168.1.1',
            'details': {'operation': 'export_logs'},
            'status': 'SUCCESS',
        }
        if data:
            base.update(data)
        self._mapping = base


def test_audit_log_row_8_mapping_fast_path():
    row = MockAuditLogRow8()
    res = _audit_log_row_to_dict(row, format_dates=True)

    assert res['audit_id'] == 'audit-123'
    assert res['user_id'] == 'user-456'
    assert res['action'] == 'ADMIN_ACTION'
    assert res['action_name'] == 'Actividad'
    assert res['resource'] == 'audit_logs'
    assert res['timestamp'] == '2026-09-22T12:00:00+00:00'
    assert res['ip_address'] == '192.168.1.1'
    assert res['user_agent'] == 'unknown'
    assert res['details'] == {'operation': 'export_logs'}
    assert res['status'] == 'SUCCESS'


def test_audit_log_row_8_mapping_null_handling():
    row = MockAuditLogRow8({
        'action': None,
        'resource': None,
        'ip_address': None,
        'details': None,
        'status': None,
    })
    res = _audit_log_row_to_dict(row, format_dates=True)

    assert res['action'] == 'UNKNOWN'
    assert res['action_name'] == 'Actividad'
    assert res['resource'] == 'unknown'
    assert res['ip_address'] == 'unknown'
    assert res['details'] == {}
    assert res['status'] == 'SUCCESS'


def test_audit_log_row_8_mapping_key_error_fallback():
    # If a row has 8 items but missing expected audit_id key, it should fall through cleanly
    row = MockAuditLogRow8({'wrong_key': 'val'})
    del row._mapping['audit_id']

    res = _audit_log_row_to_dict(row, format_dates=True)
    assert res['audit_id'] is None
    assert res['user_id'] == 'user-456'
