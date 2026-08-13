import pytest
import sys
import os
from unittest.mock import MagicMock
from app.routes import is_valid_presigned_image_url

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_leaks.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_presigned_url_max_length(app):
    """Verifica que is_valid_presigned_image_url rechace URLs extremadamente largas (> 2048 chars)."""
    with app.app_context():
        # Valid host and path format but extremely long
        valid_prefix = "https://gamevault-media-files.s3.us-east-1.amazonaws.com/covers/"
        long_url = valid_prefix + ("a" * 2000)
        assert len(long_url) > 2048
        assert not is_valid_presigned_image_url(long_url)

        # Standard normal-length URL should pass validation (when configured)
        app.config['STORAGE_BACKEND'] = 's3'
        app.config['S3_BUCKET_NAME'] = 'gamevault-media-files'
        app.config['S3_REGION'] = 'us-east-1'
        normal_url = "https://gamevault-media-files.s3.us-east-1.amazonaws.com/covers/test.png"
        assert is_valid_presigned_image_url(normal_url)

def test_teardown_removes_session(client, app):
    """Verifica que el teardown handler se ejecute al final de las peticiones para limpiar la sesión scoped de SQLAlchemy."""
    from app.models import get_session_factory
    session_factory = get_session_factory()

    # Mock the remove method on session_factory
    original_remove = session_factory.remove
    session_factory.remove = MagicMock()

    try:
        # Trigger any request to trigger teardown context
        response = client.get('/healthz')
        assert response.status_code == 200

        # Verify remove was called at least once
        assert session_factory.remove.call_count >= 1
    finally:
        # Restore the original remove method
        session_factory.remove = original_remove
