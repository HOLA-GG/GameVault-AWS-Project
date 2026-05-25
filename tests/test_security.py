import pytest
from app import create_app

@pytest.fixture
def app():
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    yield app

@pytest.fixture
def client(app):
    return app.test_client()

def test_open_redirect(client):
    # Register a user first
    client.post('/registro', data={
        'nombre': 'Test User',
        'email': 'test@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    client.post('/logout')

    # Try to login with a malicious next parameter
    response = client.post('/login?next=http://malicious.com', data={
        'email': 'test@example.com',
        'password': 'password123'
    })

    # If it's secure, it should NOT redirect to an external malicious site
    assert response.status_code == 302
    # It should either redirect to the dashboard (default) or some other safe place
    assert not response.headers['Location'].startswith('http://malicious.com')
    assert not response.headers['Location'].startswith('//malicious.com')
