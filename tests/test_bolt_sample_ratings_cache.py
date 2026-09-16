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
def reset_ratings_cache():
    """Ensure sample ratings cache is reset before and after each test."""
    from app import models
    models._SAMPLE_RATINGS_CACHE = {}
    yield
    models._SAMPLE_RATINGS_CACHE = {}


def test_sample_ratings_caching_and_invalidation(monkeypatch):
    """Verify that sample ratings are cached by subject_id, handle TTL correctly, and invalidate correctly."""
    from app import models
    from app.models import obtener_ratings_multiple, registrar_rating_showcase

    # Mock database results
    mock_results = [
        ("demo-nintendo-reliquias", 4.5, 10),
        ("demo-jrpg-esenciales", 4.0, 5),
    ]

    execute_call_count = 0

    class MockResult:
        def all(self):
            return mock_results

        def first(self):
            return (4.5, 10)

    class MockSession:
        def execute(self, *args, **kwargs):
            nonlocal execute_call_count
            execute_call_count += 1
            return MockResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    # Patch the session factory to return our MockSession
    monkeypatch.setattr(models, "get_session_factory", lambda: lambda: MockSession())

    # 1. Initially cache is empty
    assert len(models._SAMPLE_RATINGS_CACHE) == 0

    # 2. First call for Nintendo and JRPG: Should query the database and populate the cache
    subject_ids = ["demo-nintendo-reliquias", "demo-jrpg-esenciales"]
    ratings_1 = obtener_ratings_multiple("sample", subject_ids)

    assert execute_call_count == 1
    assert "demo-nintendo-reliquias" in ratings_1
    assert ratings_1["demo-nintendo-reliquias"]["average"] == 4.5
    assert ratings_1["demo-nintendo-reliquias"]["votes_count"] == 10
    assert len(models._SAMPLE_RATINGS_CACHE) == 2
    assert "demo-nintendo-reliquias" in models._SAMPLE_RATINGS_CACHE
    assert models._SAMPLE_RATINGS_CACHE["demo-nintendo-reliquias"][1]["average"] == 4.5

    # 3. Requesting different or subset IDs: Should only hit the cache for present ones, and DB for others
    # First, let's verify that requesting only "demo-nintendo-reliquias" comes from cache (no new DB call)
    ratings_nintendo = obtener_ratings_multiple("sample", ["demo-nintendo-reliquias"])
    assert execute_call_count == 1  # No DB query executed
    assert ratings_nintendo["demo-nintendo-reliquias"]["average"] == 4.5

    # Requesting a totally new ID "demo-new-id": Should trigger 1 DB query for the new ID only
    ratings_mixed = obtener_ratings_multiple("sample", ["demo-nintendo-reliquias", "demo-new-id"])
    assert execute_call_count == 2  # Incremented because of demo-new-id
    assert "demo-new-id" in ratings_mixed

    # 4. TTL expiration check: Mock time to jump ahead of TTL (30 seconds)
    # If we jump 40 seconds, the cache for demo-nintendo-reliquias should be expired and trigger a DB query
    current_time = time.time()
    monkeypatch.setattr(time, "time", lambda: current_time + 40.0)

    ratings_expired = obtener_ratings_multiple("sample", ["demo-nintendo-reliquias"])
    assert execute_call_count == 3  # DB query executed because cache was expired

    # 5. Success rating submission to sample collection should invalidate only that specific cache key
    # Reset mock time to normal
    monkeypatch.undo()

    class MockRegistrarSession:
        def scalar(self, *args, **kwargs):
            return None  # No existing rating

        def add(self, entity):
            pass

        def commit(self):
            pass

        def execute(self, *args, **kwargs):
            return MockResult()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(models, "get_session_factory", lambda: lambda: MockRegistrarSession())

    # Pre-populate cache
    obtener_ratings_multiple("sample", ["demo-nintendo-reliquias", "demo-jrpg-esenciales"])
    assert "demo-nintendo-reliquias" in models._SAMPLE_RATINGS_CACHE
    assert "demo-jrpg-esenciales" in models._SAMPLE_RATINGS_CACHE

    # Rate Nintendo showcase
    registrar_rating_showcase("sample", "demo-nintendo-reliquias", 5, "127.0.0.1")

    # Nintendo must be popped (None), while JRPG remains cached!
    assert "demo-nintendo-reliquias" not in models._SAMPLE_RATINGS_CACHE
    assert "demo-jrpg-esenciales" in models._SAMPLE_RATINGS_CACHE
