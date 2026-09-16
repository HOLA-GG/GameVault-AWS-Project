from __future__ import annotations

import sys
import time
from pathlib import Path
from unittest import mock
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_sample_collections_cache():
    """Ensure sample collections cache is reset before and after each test."""
    from app import routes
    routes._SAMPLE_COLLECTIONS_CACHE = None
    yield
    routes._SAMPLE_COLLECTIONS_CACHE = None


def test_sample_collections_cache_hit_and_invalidation(monkeypatch):
    """Verify that sample collections are cached, hit correctly, and invalidated correctly."""
    from app import routes
    from app.routes import obtener_sample_collections_cached, clear_sample_collections_cache

    apply_call_count = 0
    original_aplicar = routes.aplicar_ratings_showcase

    def mock_aplicar_ratings_showcase(*args, **kwargs):
        nonlocal apply_call_count
        apply_call_count += 1
        return original_aplicar(*args, **kwargs)

    monkeypatch.setattr(routes, "aplicar_ratings_showcase", mock_aplicar_ratings_showcase)

    # 1. Initially cache is empty
    assert routes._SAMPLE_COLLECTIONS_CACHE is None

    # 2. First call: Should calculate via aplicar_ratings_showcase and populate cache
    cols_1 = obtener_sample_collections_cached()
    assert apply_call_count == 1
    assert routes._SAMPLE_COLLECTIONS_CACHE is not None
    assert len(cols_1) == 3

    # 3. Second call: Should hit cache (no new aplicar_ratings_showcase call)
    cols_2 = obtener_sample_collections_cached()
    assert apply_call_count == 1
    assert len(cols_2) == 3

    # 4. TTL expiration: Mock time to jump ahead of TTL (30 seconds)
    current_time = time.time()
    monkeypatch.setattr(time, "time", lambda: current_time + 40.0)

    cols_expired = obtener_sample_collections_cached()
    assert apply_call_count == 2  # Re-evaluated due to TTL expiry

    # 5. Manual cache clearance
    clear_sample_collections_cache()
    assert routes._SAMPLE_COLLECTIONS_CACHE is None
