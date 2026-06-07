import os
import pytest
from app import create_app

@pytest.fixture
def app(monkeypatch):
    os.environ['APP_ENV'] = 'testing'
    # Usar DB en memoria para aislamiento total y velocidad
    db_url = "sqlite+pysqlite:///:memory:"

    # Asegurar que las variables de entorno estén seteadas antes de crear la app
    monkeypatch.setenv('DATABASE_URL', db_url)
    monkeypatch.setenv('APP_ENV', 'testing')

    # Importar app después de setear el env para que models.py tome la URL correcta
    import importlib
    import sys
    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    from app import create_app
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-key-123"
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
        '\malicious.com',
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
        assert not response.headers['Location'].startswith('\malicious.com')

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

def test_rate_showcase_csrf_protection(client):
    """Verifica que el endpoint de rating esté protegido por CSRF."""
    # Forzar habilitación de CSRF para la prueba
    client.application.config['WTF_CSRF_ENABLED'] = True

    # POST sin token CSRF
    response = client.post(
        '/api/showcase/rate',
        json={
            'subject_type': 'sample',
            'subject_id': 'demo-nintendo-reliquias',
            'rating': 5,
        }
    )

    # Debe retornar 400 Bad Request debido a la falta de token CSRF
    assert response.status_code == 400

def test_security_headers(client):
    """Verifica que las cabeceras de seguridad estén presentes y configuradas correctamente."""
    response = client.get('/')

    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'SAMEORIGIN'
    assert response.headers['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert 'upgrade-insecure-requests' in response.headers['Content-Security-Policy']
    assert 'Permissions-Policy' in response.headers
    assert 'camera=()' in response.headers['Permissions-Policy']

def test_hsts_header_in_production(app):
    """Verifica que HSTS esté presente en producción."""
    app.config['APP_ENV'] = 'production'
    with app.test_client() as client:
        response = client.get('/')
        assert 'Strict-Transport-Security' in response.headers
        assert 'max-age=31536000' in response.headers['Strict-Transport-Security']

def test_hsts_header_not_in_dev(app):
    """Verifica que HSTS no esté presente en desarrollo/test por defecto."""
    app.config['APP_ENV'] = 'testing'
    with app.test_client() as client:
        response = client.get('/')
        assert 'Strict-Transport-Security' not in response.headers

def test_rate_limiting_demo(client):
    """Verifica que el límite de tasa en el endpoint de demo esté funcionando."""
    # El límite es 5 por minuto
    for _ in range(5):
        response = client.post('/demo', data={'titulo': 'Test'}, follow_redirects=True)
        assert response.status_code == 200

    # El sexto intento debería ser bloqueado
    response = client.post('/demo', data={'titulo': 'Test'}, follow_redirects=True)
    assert response.status_code == 429
    assert b'Demasiados intentos' in response.data

def test_stale_session_inactive_user(client):
    """Verifica que un usuario desactivado sea bloqueado a pesar de tener una sesión activa."""
    from app.models import get_session_factory, User, generate_password_hash, select

    # 1. Crear usuario en DB
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='stale-id',
            email='stale@example.com',
            nombre='Stale',
            password_hash=generate_password_hash('password'),
            status='active',
            role='user'
        )
        db_session.add(user)
        db_session.commit()

    # 2. Inyectar en sesión
    with client.session_transaction() as sess:
        sess['user_id'] = 'stale-id'

    # Verificar que el acceso funciona
    response = client.get('/dashboard')
    assert response.status_code == 200

    # 3. Desactivar el usuario en DB
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.user_id == 'stale-id'))
        user.status = 'inactive'
        db_session.commit()

    # 4. Intentar acceder
    response = client.get('/dashboard', follow_redirects=True)

    assert b'Tu sesi\xc3\xb3n ha expirado o tu cuenta ya no est\xc3\xa1 activa.' in response.data
    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_stale_session_role_change(client):
    """Verifica que un cambio de rol se aplique inmediatamente."""
    from app.models import get_session_factory, User, generate_password_hash, select

    # 1. Crear usuario en DB
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id='role-id',
            email='role@example.com',
            nombre='Role',
            password_hash=generate_password_hash('password'),
            status='active',
            role='user'
        )
        db_session.add(user)
        db_session.commit()

    # 2. Inyectar en sesión
    with client.session_transaction() as sess:
        sess['user_id'] = 'role-id'

    # 3. Intentar acceder al panel admin (debe fallar)
    response = client.get('/admin', follow_redirects=True)
    # Al fallar el require_admin, redirige al dashboard por defecto
    assert response.status_code == 200
    assert b'Acceso denegado. Solo administradores.' in response.data

    # 4. Promover a admin en DB
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.user_id == 'role-id'))
        user.role = 'admin'
        db_session.commit()

    # 5. Intentar acceder al panel admin (debe funcionar)
    response = client.get('/admin')
    assert response.status_code == 200
    assert b'Usuarios registrados' in response.data
