import pytest
import os
from app import create_app
from app.models import get_session_factory, User, select

@pytest.fixture
def app():
    db_path = 'gamevault_test_stale.db'
    if os.path.exists(db_path):
        os.remove(db_path)

    os.environ['DATABASE_URL'] = f'sqlite+pysqlite:///{db_path}'
    os.environ['APP_ENV'] = 'testing'

    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    yield app

    if os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def client(app):
    return app.test_client()

def test_stale_admin_session(client):
    # 1. Register a user
    client.post('/registro', data={
        'nombre': 'Stale User',
        'email': 'stale@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    client.post('/logout')

    # 2. Make them admin in DB manually
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == 'stale@example.com'))
        user.role = 'admin'
        db_session.commit()

    # 3. Login - now they have admin session
    client.post('/login', data={
        'email': 'stale@example.com',
        'password': 'password123'
    })

    # Verify they can access admin panel
    response = client.get('/admin')
    assert response.status_code == 200

    # 4. Demote them in DB
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == 'stale@example.com'))
        user.role = 'user'
        db_session.commit()

    # 5. Try to access admin panel again with the SAME session
    response = client.get('/admin')

    # Should now pass with 302
    assert response.status_code == 302

def test_inactive_user_session(client):
    # 1. Register
    client.post('/registro', data={
        'nombre': 'Inactive User',
        'email': 'inactive@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })
    client.post('/logout')

    # 2. Deactivate user in DB BEFORE login
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == 'inactive@example.com'))
        user.status = 'inactive'
        db_session.commit()

    # 3. Try to Login
    response = client.post('/login', data={
        'email': 'inactive@example.com',
        'password': 'password123'
    }, follow_redirects=True)

    # Should be back on login page with error
    assert b'Email o contrase\xc3\xb1a incorrectos' in response.data

def test_deactivated_while_logged_in(client):
    # 1. Register and login
    client.post('/registro', data={
        'nombre': 'Active User',
        'email': 'active@example.com',
        'password': 'password123',
        'confirm_password': 'password123'
    })

    # Verify access
    response = client.get('/dashboard')
    assert response.status_code == 200

    # 2. Deactivate in DB
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = db_session.scalar(select(User).where(User.email == 'active@example.com'))
        user.status = 'inactive'
        db_session.commit()

    # 3. Access dashboard
    response = client.get('/dashboard')
    assert response.status_code == 302
    assert '/login' in response.headers.get('Location', '')
