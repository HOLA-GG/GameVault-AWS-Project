"""Tests for Bolt lock-free cache read optimizations in app/models.py and app/routes.py."""

import time
from unittest.mock import MagicMock, patch
from flask import Flask
from app.models import (
    _SIGNED_URLS_CACHE,
    _VALID_IP_CACHE,
    _PUBLIC_COLLECTIONS_CACHE,
    _LOG_STATS_CACHE,
    crear_url_firmada_lectura,
    sanitize_and_validate_ip,
    obtener_colecciones_publicas,
    obtener_estadisticas_logs,
)
from app.routes import (
    _SAMPLE_COLLECTIONS_CACHE,
    obtener_sample_collections_cached,
)
import app.routes as routes_module
import app.models as models_module


def test_sanitize_and_validate_ip_cache_hit():
    """Verify sanitize_and_validate_ip returns cached IP directly via lock-free path."""
    test_ip = "192.168.1.100"
    _VALID_IP_CACHE[test_ip] = "192.168.1.100"

    res = sanitize_and_validate_ip(test_ip)
    assert res == "192.168.1.100"


def test_crear_url_firmada_lectura_cache_hit():
    """Verify crear_url_firmada_lectura returns cached presigned URL directly via lock-free path."""
    app = Flask(__name__)
    app.config['STORAGE_BACKEND'] = 'r2'

    test_url = "https://example-bucket.s3.amazonaws.com/covers/test_game.jpg"
    now = time.time()
    expires_in = 3600
    cache_key = f"{test_url}:{expires_in}"
    signed_target = "https://example-bucket.r2.cloudflarestorage.com/covers/test_game.jpg?X-Amz-Signature=123"

    _SIGNED_URLS_CACHE[cache_key] = (now, now + expires_in, signed_target)

    with app.app_context():
        res = crear_url_firmada_lectura(test_url, expires_in=expires_in)
        assert res == signed_target


def test_obtener_sample_collections_cached_lockfree():
    """Verify obtener_sample_collections_cached hits cache directly without lock contention."""
    now = time.time()
    mock_data = [{'id': 'demo-1', 'title': 'Demo 1', 'average_rating': 4.5}]
    routes_module._SAMPLE_COLLECTIONS_CACHE = (now, mock_data)

    res = obtener_sample_collections_cached()
    assert len(res) == 1
    assert res[0]['id'] == 'demo-1'
    routes_module._SAMPLE_COLLECTIONS_CACHE = None


def test_obtener_colecciones_publicas_lockfree():
    """Verify obtener_colecciones_publicas hits cache directly without lock contention."""
    now = time.time()
    mock_data = [{'user_id': 'u1', 'owner_name': 'Test User'}]
    models_module._PUBLIC_COLLECTIONS_CACHE[6] = (now, mock_data)

    res = obtener_colecciones_publicas(limit=6)
    assert len(res) == 1
    assert res[0]['user_id'] == 'u1'
    models_module._PUBLIC_COLLECTIONS_CACHE.clear()


def test_obtener_estadisticas_logs_lockfree():
    """Verify obtener_estadisticas_logs hits cache directly without lock contention."""
    now = time.time()
    mock_stats = {'total_logs': 42, 'status_counts': {'SUCCESS': 42}, 'top_users': [], 'success_rate': 100.0}
    models_module._LOG_STATS_CACHE = (now, mock_stats)

    res = obtener_estadisticas_logs()
    assert res['total_logs'] == 42
    models_module._LOG_STATS_CACHE = None
