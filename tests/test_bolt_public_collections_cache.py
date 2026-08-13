from __future__ import annotations

import sys
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def reset_public_collections_cache():
    """Ensure public collections cache is reset before and after each test."""
    from app import models
    models._PUBLIC_COLLECTIONS_CACHE = {}
    yield
    models._PUBLIC_COLLECTIONS_CACHE = {}


def test_public_collections_caching_and_invalidation(monkeypatch):
    """Verify that public collections are cached, respect TTL, and invalidate on write paths."""
    from app import models
    from app.models import (
        obtener_colecciones_publicas,
        clear_public_collections_cache,
        registrar_rating_showcase,
    )

    # Mock database results
    mock_collections = [
        {
            'user_id': 'u1',
            'owner_name': 'Alice',
            'owner_email': 'alice@test.com',
            'collection_visibility': 'public',
            'homepage_showcase_opt_in': True,
            'total_games': 10,
            'favorites_count': 3,
            'average_rating': 4.5,
            'last_updated_at': '2026-08-27T00:00:00Z',
            'dominant_platform': 'Nintendo',
            'showcase_rating_average': 4.0,
            'showcase_votes_count': 5,
        }
    ]

    db_call_count = 0

    def mock_obtener_resumenes_colecciones(visibility=None, limit=None, offset=None, homepage_only=False):
        nonlocal db_call_count
        db_call_count += 1
        return mock_collections

    monkeypatch.setattr(models, "obtener_resumenes_colecciones", mock_obtener_resumenes_colecciones)

    # 1. Initially empty cache
    assert len(models._PUBLIC_COLLECTIONS_CACHE) == 0

    # 2. First call: queries the database and caches results
    res1 = obtener_colecciones_publicas(limit=6)
    assert db_call_count == 1
    assert len(res1) == 1
    assert res1[0]['owner_name'] == 'Alice'
    assert len(models._PUBLIC_COLLECTIONS_CACHE) == 1

    # 3. Second call: should serve from cache (no database query)
    res2 = obtener_colecciones_publicas(limit=6)
    assert db_call_count == 1
    assert len(res2) == 1
    assert res2[0]['owner_name'] == 'Alice'

    # 4. TTL expiration check: mock time to jump ahead of TTL (15 seconds)
    current_time = time.time()
    monkeypatch.setattr(time, "time", lambda: current_time + 20.0)

    res3 = obtener_colecciones_publicas(limit=6)
    assert db_call_count == 2  # Incremented because cache was expired

    # 5. Test manual clear
    clear_public_collections_cache()
    assert len(models._PUBLIC_COLLECTIONS_CACHE) == 0

    # 6. Test invalidation triggers (we can mock the actual actions/commits)
    # Let's populate the cache first
    # Reset mock time to normal
    monkeypatch.undo()
    monkeypatch.setattr(models, "obtener_resumenes_colecciones", mock_obtener_resumenes_colecciones)

    obtener_colecciones_publicas(limit=6)
    assert len(models._PUBLIC_COLLECTIONS_CACHE) == 1

    # Invalidate via registrar_rating_showcase with subject_type='public'
    # Mocking database operations for registrar_rating_showcase
    class MockSession:
        def scalar(self, *args, **kwargs):
            return None
        def add(self, entity):
            pass
        def commit(self):
            pass
        def execute(self, *args, **kwargs):
            class RowMock:
                def first(self):
                    return (4.5, 1)
            return RowMock()
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass

    monkeypatch.setattr(models, "get_session_factory", lambda: lambda: MockSession())

    # Mock obtener_rating_showcase to avoid hitting raw DB
    monkeypatch.setattr(models, "obtener_rating_showcase", lambda st, sid: {'average': 4.5, 'votes_count': 1})

    registrar_rating_showcase('public', 'u1', 5, '127.0.0.1')
    assert len(models._PUBLIC_COLLECTIONS_CACHE) == 0  # Invalidation happened!
