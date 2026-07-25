import pytest
import sys
import os
import uuid
from flask import g
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = f'gamevault_test_sentry_rid_{uuid.uuid4().hex}.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    # Set a mock SENTRY_DSN so Sentry is actually initialized in create_app
    monkeypatch.setenv('SENTRY_DSN', 'https://pub@sentry.io/1234')

    # Force reload of app components
    modules_to_reload = ['app', 'app.models', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
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

def test_request_id_truncation(client):
    """Verifies that an extremely long X-Request-Id header is truncated to 100 characters."""
    long_id = "a" * 150
    response = client.get('/', headers={'X-Request-Id': long_id})
    assert response.status_code == 200

    # Check that the response header returns the truncated request ID
    returned_id = response.headers.get('X-Request-Id')
    assert returned_id is not None
    assert len(returned_id) == 100
    assert returned_id == "a" * 100

def test_sentry_before_send_redaction(app):
    """Verifies that Sentry's before_send hook correctly redacts sensitive event data."""
    # Find Sentry's init_sdk options
    import sentry_sdk
    client = sentry_sdk.Hub.current.client
    assert client is not None

    before_send = client.options.get('before_send')
    assert before_send is not None

    # Mock event with sensitive fields
    mock_event = {
        'message': 'Error occurred',
        'request': {
            'headers': {
                'Cookie': 'session=abc123secret'
            },
            'data': {
                'password': 'MySecretPassword123',
                'token': 'supersecrettoken'
            }
        },
        'extra': {
            'api_key': '12345-api-key',
            'user': {
                'email': 'user@example.com',
                'telefono': '555123456'
            }
        }
    }

    # Run event through Sentry's before_send callback
    redacted_event = before_send(mock_event, None)

    # Assert sensitive keys are redacted
    assert redacted_event['request']['headers']['Cookie'] == '[REDACTED]'
    assert redacted_event['request']['data']['password'] == '[REDACTED]'
    assert redacted_event['request']['data']['token'] == '[REDACTED]'
    assert redacted_event['extra']['api_key'] == '[REDACTED]'
    assert redacted_event['extra']['user']['telefono'] == '[REDACTED]'
    # Non-sensitive keys should remain unchanged
    assert redacted_event['message'] == 'Error occurred'
    assert redacted_event['extra']['user']['email'] == 'user@example.com'
