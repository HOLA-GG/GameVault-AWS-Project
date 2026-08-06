from __future__ import annotations

import os
import sys
import time
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import models


def test_signed_url_cache_bypasses_signature(monkeypatch):
    """Verify that cached URLs do not trigger s3_client.generate_presigned_url calls."""
    # Reset/Mock Cache config
    monkeypatch.setattr(models, '_SIGNED_URLS_CACHE', {})
    monkeypatch.setattr(models, 'STORAGE_BACKEND', 'r2')
    monkeypatch.setenv('R2_BUCKET_NAME', 'test-bucket')

    called_count = 0

    class MockS3Client:
        def generate_presigned_url(self, method, Params, ExpiresIn):
            nonlocal called_count
            called_count += 1
            return f"https://signed-url.com/{Params['Key']}?expires={ExpiresIn}"

    # Patch S3 client acquisition and storage backend
    monkeypatch.setattr(models, '_get_s3_client', lambda: MockS3Client())

    # Mock app config context to return r2
    class MockApp:
        config = {'STORAGE_BACKEND': 'r2'}

    monkeypatch.setattr(models, 'current_app', MockApp())

    # First call - cache miss
    img_url = "https://r2.cloudflarestorage.com/test-bucket/covers/my_image.png"
    url1 = models.crear_url_firmada_lectura(img_url, expires_in=1200)
    assert called_count == 1
    assert "covers/my_image.png" in url1

    # Second call - cache hit
    url2 = models.crear_url_firmada_lectura(img_url, expires_in=1200)
    assert called_count == 1
    assert url1 == url2


def test_signed_url_cache_ttl_expiration(monkeypatch):
    """Verify that cached items expire once absolute expiry has passed."""
    monkeypatch.setattr(models, '_SIGNED_URLS_CACHE', {})
    monkeypatch.setattr(models, 'STORAGE_BACKEND', 'r2')
    monkeypatch.setenv('R2_BUCKET_NAME', 'test-bucket')

    called_count = 0

    class MockS3Client:
        def generate_presigned_url(self, method, Params, ExpiresIn):
            nonlocal called_count
            called_count += 1
            return f"https://signed-url.com/{Params['Key']}?sig={called_count}"

    monkeypatch.setattr(models, '_get_s3_client', lambda: MockS3Client())

    class MockApp:
        config = {'STORAGE_BACKEND': 'r2'}

    monkeypatch.setattr(models, 'current_app', MockApp())

    img_url = "https://r2.cloudflarestorage.com/test-bucket/covers/my_image.png"

    # Fetch once to populate cache
    url1 = models.crear_url_firmada_lectura(img_url, expires_in=1200)
    assert called_count == 1

    # Fake absolute expiration to be in the past
    cache_key = f"{img_url}:1200"
    models._SIGNED_URLS_CACHE[cache_key] = (time.time() - 3600.0, time.time() - 2400.0, url1)

    # Next call should trigger a cache miss and regenerate because it's expired
    url2 = models.crear_url_firmada_lectura(img_url, expires_in=1200)
    assert called_count == 2
    assert url1 != url2


def test_signed_url_cache_fifo_eviction(monkeypatch):
    """Verify that cache doesn't grow indefinitely and respects MAX_CAPACITY with FIFO eviction."""
    monkeypatch.setattr(models, '_SIGNED_URLS_CACHE', {})
    monkeypatch.setattr(models, '_SIGNED_URLS_MAX_CAPACITY', 3)
    monkeypatch.setattr(models, 'STORAGE_BACKEND', 'r2')
    monkeypatch.setenv('R2_BUCKET_NAME', 'test-bucket')

    class MockS3Client:
        def generate_presigned_url(self, method, Params, ExpiresIn):
            return f"https://signed-url.com/{Params['Key']}"

    monkeypatch.setattr(models, '_get_s3_client', lambda: MockS3Client())

    class MockApp:
        config = {'STORAGE_BACKEND': 'r2'}

    monkeypatch.setattr(models, 'current_app', MockApp())

    # We will generate urls for image1, image2, image3, image4
    urls = [
        "https://r2.cloudflarestorage.com/test-bucket/covers/img1.png",
        "https://r2.cloudflarestorage.com/test-bucket/covers/img2.png",
        "https://r2.cloudflarestorage.com/test-bucket/covers/img3.png",
        "https://r2.cloudflarestorage.com/test-bucket/covers/img4.png",
    ]

    for url in urls[:3]:
        models.crear_url_firmada_lectura(url, expires_in=1200)

    # Cache should contain exactly 3 items (img1, img2, img3)
    assert len(models._SIGNED_URLS_CACHE) == 3
    assert f"{urls[0]}:1200" in models._SIGNED_URLS_CACHE

    # Push fourth item to trigger eviction
    models.crear_url_firmada_lectura(urls[3], expires_in=1200)

    # Cache should still be at capacity (3) and first item (img1) should be evicted
    assert len(models._SIGNED_URLS_CACHE) == 3
    assert f"{urls[0]}:1200" not in models._SIGNED_URLS_CACHE
    assert f"{urls[3]}:1200" in models._SIGNED_URLS_CACHE


def test_expires_in_dynamic_evaluation(monkeypatch):
    """Verify that using different expires_in on the same URL results in correct separate cached lifetimes."""
    monkeypatch.setattr(models, '_SIGNED_URLS_CACHE', {})
    monkeypatch.setattr(models, 'STORAGE_BACKEND', 'r2')
    monkeypatch.setenv('R2_BUCKET_NAME', 'test-bucket')

    called_count = 0

    class MockS3Client:
        def generate_presigned_url(self, method, Params, ExpiresIn):
            nonlocal called_count
            called_count += 1
            return f"https://signed-url.com/{Params['Key']}?exp={ExpiresIn}"

    monkeypatch.setattr(models, '_get_s3_client', lambda: MockS3Client())

    class MockApp:
        config = {'STORAGE_BACKEND': 'r2'}

    monkeypatch.setattr(models, 'current_app', MockApp())

    img_url = "https://r2.cloudflarestorage.com/test-bucket/covers/my_image.png"

    # Request with 500s expiration
    models.crear_url_firmada_lectura(img_url, expires_in=500)
    # Request with 2000s expiration
    models.crear_url_firmada_lectura(img_url, expires_in=2000)

    # Both must have been generated independently because different expires_in values are part of the cache key
    assert called_count == 2
