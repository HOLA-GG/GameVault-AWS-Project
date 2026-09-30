"""
tests/test_bolt_dict_status_results.py - Verifies status_counts dict construction optimization.
"""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import app.models as models
from app.models import AuditLog
from sqlalchemy import func, select


def test_dict_status_results_equivalence(monkeypatch):
    """Verifies that dict(status_results) produces identical status counts dictionary in obtener_estadisticas_logs."""
    models.clear_log_stats_cache()

    class MockResult:
        def __init__(self, data):
            self.data = data

        def all(self):
            return self.data

    class MockSession:
        def execute(self, select_stmt, *args, **kwargs):
            stmt_str = str(select_stmt)
            if "group_by(audit_logs.status)" in stmt_str or "status" in stmt_str:
                return MockResult([("SUCCESS", 12), ("FAILED", 3), ("ERROR", 1)])
            return MockResult([("user-1", 10), ("user-2", 6)])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(models, "get_session_factory", lambda: lambda: MockSession())

    with models.get_session_factory()() as session:
        status_results = session.execute(
            select(AuditLog.status, func.count(AuditLog.audit_id)).group_by(AuditLog.status)
        ).all()

    # Verify dict(status_results) matches dict comprehension
    expected_dict = {row[0]: row[1] for row in status_results}
    fast_dict = dict(status_results)

    assert fast_dict == expected_dict
    assert fast_dict == {"SUCCESS": 12, "FAILED": 3, "ERROR": 1}

    # Verify function returns exact stats
    stats = models.obtener_estadisticas_logs()
    assert stats["status_counts"] == {"SUCCESS": 12, "FAILED": 3, "ERROR": 1}
    assert stats["total_logs"] == 16
