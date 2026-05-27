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

def test_open_redirect_bypass_attempts(client):
    # Register a user first
    client.post('/registro', data={
        'nombre': 'Test User',
        'email': 'bypass@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    client.post('/logout')

    # Test various bypass attempts
    bypasses = [
        '///malicious.com',
        '\\malicious.com',
        '//malicious.com',
        'https:malicious.com'
    ]

    for target in bypasses:
        response = client.post(f'/login?next={target}', data={
            'email': 'bypass@example.com',
            'password': 'password123'
        })
        assert response.status_code == 302
        assert not response.headers['Location'].startswith('http://malicious.com')
        assert not response.headers['Location'].startswith('https://malicious.com')
        assert not response.headers['Location'].startswith('//malicious.com')
        assert not response.headers['Location'].startswith('\\malicious.com')

def test_forgot_password_manual_token_enumeration(client):
    app = client.application
    app.config['SHOW_RESET_DEBUG_TOKEN'] = False

    # Attempt recovery with non-existent data
    response = client.post('/forgot-password/manual-token', data={
        'email': 'nonexistent@example.com',
        'telefono': '000000000'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Si tus datos coinciden, se ha procesado la solicitud' in response.data
    assert b'No se pudo validar los datos' not in response.data

    # Attempt recovery with valid email but wrong phone
    client.post('/registro', data={
        'nombre': 'Enum User',
        'email': 'enum@example.com',
        'telefono': '123456789',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    client.post('/logout')

    response = client.post('/forgot-password/manual-token', data={
        'email': 'enum@example.com',
        'telefono': '999999999'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Si tus datos coinciden, se ha procesado la solicitud' in response.data
    assert b'No se pudo validar los datos' not in response.data
