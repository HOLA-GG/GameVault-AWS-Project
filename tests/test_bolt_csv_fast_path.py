import pytest
from app.models import exportar_logs_csv, _sanitize_csv_val

def test_sanitize_csv_val_fast_path():
    """Verify that _sanitize_csv_val correctly handles normal strings, leading whitespace, and CSV injection symbols."""
    # Normal safe values
    assert _sanitize_csv_val("SUCCESS") == "SUCCESS"
    assert _sanitize_csv_val("CREATE_GAME") == "CREATE_GAME"
    assert _sanitize_csv_val("127.0.0.1") == "127.0.0.1"
    assert _sanitize_csv_val("") == ""

    # Values starting directly with risky symbols
    assert _sanitize_csv_val("=SUM(1,2)") == "'=SUM(1,2)"
    assert _sanitize_csv_val("+12345") == "'+12345"
    assert _sanitize_csv_val("-100") == "'-100"
    assert _sanitize_csv_val("@admin") == "'@admin"
    assert _sanitize_csv_val("|pipe") == "'|pipe"
    assert _sanitize_csv_val("`command") == "'`command"

    # Values with leading whitespace followed by risky symbols
    assert _sanitize_csv_val("  =cmd|' /c calc'!A0") == "'  =cmd|' /c calc'!A0"
    assert _sanitize_csv_val("   @games") == "'   @games"

    # Values with leading whitespace but safe characters
    assert _sanitize_csv_val("   normal text") == "   normal text"

def test_exportar_logs_csv_integration():
    """Verify exportar_logs_csv output with fast path sanitization."""
    logs = [
        {
            'audit_id': 'log1',
            'user_id': 'u1',
            'action': ' =cmd|calc',
            'resource': 'games',
            'timestamp': '2026-09-08T12:00:00+00:00',
            'ip_address': '192.168.1.1',
            'status': 'SUCCESS',
            'details': {'note': '@admin'}
        }
    ]
    csv_out = exportar_logs_csv(logs)
    lines = csv_out.splitlines()
    assert lines[0] == 'audit_id,user_id,action,resource,timestamp,ip_address,status,details'
    assert "' =cmd|calc" in lines[1]
    assert "'@admin" in lines[1]
