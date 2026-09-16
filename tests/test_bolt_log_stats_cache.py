from __future__ import annotations

import sys
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_log_stats_cache():
    """Ensure audit log stats cache is reset before and after each test."""
    from app import models
    models.clear_log_stats_cache()
    yield
    models.clear_log_stats_cache()


def test_log_stats_caching_and_expiration(monkeypatch):
    """Verify that log statistics are cached, respect TTL (15s), and can be manually cleared."""
    from app import models
    from app.models import obtener_estadisticas_logs, clear_log_stats_cache

    execute_call_count = 0

    class MockResult:
        def __init__(self, data):
            self.data = data

        def all(self):
            return self.data

    class MockSession:
        def execute(self, select_stmt, *args, **kwargs):
            nonlocal execute_call_count
            execute_call_count += 1
            # Mock results for status grouping (e.g. 5 SUCCESS, 1 FAILED) or top users
            # The first select is grouping by status
            stmt_str = str(select_stmt)
            if "group_by(audit_logs.status)" in stmt_str or "status" in stmt_str:
                return MockResult([("SUCCESS", 5), ("FAILED", 1)])
            # The second select is top users
            return MockResult([("user-1", 4), ("user-2", 2)])

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch the session factory to return our MockSession
    monkeypatch.setattr(models, "get_session_factory", lambda: lambda: MockSession())

    # 1. Initially, the cache is None
    assert models._LOG_STATS_CACHE is None

    # 2. First call: Should query the database and populate the cache
    stats_1 = obtener_estadisticas_logs()
    assert execute_call_count == 2  # 1 for status, 1 for top users
    assert stats_1["total_logs"] == 6
    assert stats_1["status_counts"] == {"SUCCESS": 5, "FAILED": 1}
    assert stats_1["success_rate"] == 83.33
    assert len(stats_1["top_users"]) == 2

    # Verify cache is populated
    assert models._LOG_STATS_CACHE is not None
    cached_time, cached_data = models._LOG_STATS_CACHE
    assert cached_data["total_logs"] == 6

    # 3. Second call: Should read from cache without executing database queries
    stats_2 = obtener_estadisticas_logs()
    assert execute_call_count == 2  # No extra database calls
    assert stats_2["total_logs"] == 6

    # 4. TTL expiration check: Mock time to jump past TTL (15s)
    current_time = time.time()
    monkeypatch.setattr(time, "time", lambda: current_time + 20.0)

    # Calling again should trigger DB calls because of expiration
    stats_3 = obtener_estadisticas_logs()
    assert execute_call_count == 4  # DB query executed because cache was expired
    assert stats_3["total_logs"] == 6

    # 5. Manual clearing of cache
    clear_log_stats_cache()
    assert models._LOG_STATS_CACHE is None

    # Another call should hit DB again
    stats_4 = obtener_estadisticas_logs()
    assert execute_call_count == 6
