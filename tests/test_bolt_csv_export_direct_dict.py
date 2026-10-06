import unittest
from app.models import exportar_logs_csv, _sanitize_csv_val

class TestBoltCSVExportDirectDict(unittest.TestCase):
    def test_exportar_logs_csv_complete_and_sparse_records(self):
        logs = [
            {
                'audit_id': 'log-1',
                'user_id': 'usr-1',
                'action': 'LOGIN',
                'resource': 'auth',
                'timestamp': '2026-03-31T12:00:00Z',
                'ip_address': '127.0.0.1',
                'status': 'SUCCESS',
                'details': {'ip': '127.0.0.1'}
            },
            {
                'audit_id': 'log-2',
                'user_id': '=CMD()',
                'action': 'EXPORT',
                'resource': 'logs',
                'timestamp': '2026-03-31T12:01:00Z',
                'ip_address': '10.0.0.1',
                'status': 'SUCCESS',
                'details': None
            },
            {
                'audit_id': 'log-3',
                'user_id': 'usr-3',
                'action': 'LOGOUT',
                'resource': 'auth',
                'timestamp': '2026-03-31T12:02:00Z',
                'ip_address': '10.0.0.2',
                'status': 'SUCCESS',
                'details': ''
            },
            # Sparse log record missing keys to trigger KeyError fallback path
            {
                'audit_id': 'log-4',
                'action': 'LOGOUT',
                'details': ''
            }
        ]

        csv_output = exportar_logs_csv(logs)
        lines = [line.strip() for line in csv_output.strip().split('\r\n') if line.strip()]
        if len(lines) != 5:
            lines = [line.strip() for line in csv_output.strip().split('\n') if line.strip()]

        self.assertEqual(len(lines), 5)
        self.assertEqual(lines[0], 'audit_id,user_id,action,resource,timestamp,ip_address,status,details')

        # Row 1 check
        self.assertIn('log-1,usr-1,LOGIN,auth,2026-03-31T12:00:00Z,127.0.0.1,SUCCESS', lines[1])

        # Row 2 check (CSV injection formula prefix sanitization)
        self.assertIn("'=CMD()", lines[2])

        # Row 3 check (Falsy/empty string details on full record)
        self.assertEqual(lines[3], 'log-3,usr-3,LOGOUT,auth,2026-03-31T12:02:00Z,10.0.0.2,SUCCESS,{}')

        # Row 4 check (Sparse log matches full record output: audit_id=log-4, user_id='', action=LOGOUT, resource='', timestamp='', ip_address='', status='', details='{}')
        self.assertEqual(lines[4], 'log-4,,LOGOUT,,,,,{}')

if __name__ == '__main__':
    unittest.main()
