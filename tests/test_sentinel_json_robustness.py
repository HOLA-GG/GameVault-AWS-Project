import pytest
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def client():
    os.environ['APP_ENV'] = 'testing'
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

    # Reload modules to ensure they use the testing environment
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.test_client() as client:
        yield client

def test_rate_showcase_malformed_json(client):
    """Verify that sending a JSON list instead of a dict doesn't crash the server."""
    response = client.post('/api/showcase/rate', json=["not", "a", "dict"])
    assert response.status_code == 400
    assert response.get_json() == {'error': 'Datos de valoración inválidos.'}
