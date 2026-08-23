from datetime import datetime, timezone
from app.models import _audit_log_row_to_dict

class FakeMappingRow:
    def __init__(self, mapping_dict):
        self._mapping = mapping_dict


def test_audit_log_row_to_dict_length_6_projection():
    now = datetime.now(timezone.utc)
    # 6-column projection for audit logs: timestamp, action, action_name, resource, status, details
    m_dict = {
        'timestamp': now,
        'action': 'CHANGE_PASSWORD',
        'action_name': 'Cambiar contraseña',
        'resource': 'users',
        'status': 'SUCCESS',
        'details': {'test': 'data'},
    }
    row = FakeMappingRow(m_dict)

    res_formatted = _audit_log_row_to_dict(row, format_dates=True)
    assert res_formatted['action'] == 'CHANGE_PASSWORD'
    assert res_formatted['action_name'] == 'Cambiar contraseña'
    assert res_formatted['resource'] == 'users'
    assert res_formatted['status'] == 'SUCCESS'
    assert res_formatted['details'] == {'test': 'data'}
    assert res_formatted['timestamp'] == now.isoformat()
    assert res_formatted['audit_id'] is None
    assert res_formatted['user_id'] is None
    assert res_formatted['ip_address'] == 'unknown'
    assert res_formatted['user_agent'] == 'unknown'

    res_raw = _audit_log_row_to_dict(row, format_dates=False)
    assert res_raw['timestamp'] == now
