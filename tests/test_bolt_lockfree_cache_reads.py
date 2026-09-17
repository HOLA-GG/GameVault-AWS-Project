"""Tests for Bolt lock-free cache read optimizations in app/models.py."""

import time
from unittest.mock import MagicMock, patch
from flask import Flask
from app.models import (
    _SIGNED_URLS_CACHE,
    _VALID_IP_CACHE,
    crear_url_firmada_lectura,
    sanitize_and_validate_ip,
)


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
