"""Tests for presigned upload STORAGE_BACKEND dynamic config and filename sanitization."""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_presign_config_hardening.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('STORAGE_BACKEND', 'local')
    monkeypatch.setenv('R2_BUCKET_NAME', 'test-bucket')
    monkeypatch.setenv('R2_ENDPOINT_URL', 'https://r2.example.com')

    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    from app import create_app
    app_instance = create_app()
    app_instance.config['TESTING'] = True

    yield app_instance

    if os.path.exists(db_file):
        os.remove(db_file)


def test_crear_presigned_upload_respects_app_config(app, monkeypatch):
    from app.models import crear_presigned_upload

    # Mock S3 client for presigned post generation
    mock_s3_client = MagicMock()
    mock_s3_client.generate_presigned_post.return_value = {
        'url': 'https://r2.example.com/test-bucket',
        'fields': {},
    }
    monkeypatch.setattr('app.models._get_s3_client', lambda: mock_s3_client)

    with app.app_context():
        # Set app config to r2
        app.config['STORAGE_BACKEND'] = 'r2'

        result = crear_presigned_upload('../../../malicious_name.png', 'image/png', 5 * 1024 * 1024)
        assert result is not None
        assert 'object_url' in result
        # Verify path traversal in filename was sanitized out
        assert '../../../' not in result['object_url']
        assert 'malicious_name.png' in result['object_url']

        # Verify raising RuntimeError if app.config STORAGE_BACKEND is disabled
        app.config['STORAGE_BACKEND'] = 'none'
        with pytest.raises(RuntimeError) as exc_info:
            crear_presigned_upload('cover.png', 'image/png', 5 * 1024 * 1024)
        assert 'none' in str(exc_info.value)
