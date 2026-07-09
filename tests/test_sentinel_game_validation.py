import pytest
import uuid
import sys
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_validation.db'
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

def login_session(client):
    from app.models import get_session_factory, User
    from werkzeug.security import generate_password_hash
    import hashlib

    user_id = 'val-user-1'
    email = 'val@example.com'
    pw_hash = generate_password_hash('SecurePass123!')

    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id=user_id,
            email=email,
            nombre='Validator',
            password_hash=pw_hash,
            role='user',
            status='active'
        )
        db_session.add(user)
        db_session.commit()

    with client.session_transaction() as session:
        session['user_id'] = user_id
        session['email'] = email
        session['nombre'] = 'Validator'
        session['role'] = 'user'
        session['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

def test_invalid_metadata_normalized(client):
    """Verifica que se normalizan valores inválidos para plataforma y estado."""
    login_session(client)

    # 1. Test invalid options
    response = client.post('/agregar', data={
        'titulo': 'Invalid Game',
        'descripcion': 'Test description',
        'plataforma': 'Malicious Platform',
        'estado': 'Malicious State',
        'categoria': 'Biblioteca',
        'prioridad': 'Media'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'Invalid Game' in response.data

    from app.models import get_session_factory, Game, select
    session_factory = get_session_factory()
    with session_factory() as session:
        game = session.scalar(select(Game).where(Game.titulo == 'Invalid Game'))
        assert game is not None
        # Should be normalized to defaults
        assert game.plataforma == 'PC'
        assert game.estado == 'N/A'

def test_overly_long_metadata_rejected(client):
    """Verifica que valores excesivamente largos son rechazados con un mensaje de error."""
    login_session(client)

    long_string = 'A' * 81 # Database limit is 80

    response = client.post('/agregar', data={
        'titulo': 'Long Metadata Game',
        'descripcion': 'Test description',
        'plataforma': long_string,
        'estado': 'N/A',
        'categoria': 'Biblioteca',
        'prioridad': 'Media'
    }, follow_redirects=True)

    assert response.status_code == 200
    assert b'El nombre de la plataforma es demasiado largo' in response.data

    from app.models import get_session_factory, Game, select
    session_factory = get_session_factory()
    with session_factory() as session:
        game = session.scalar(select(Game).where(Game.titulo == 'Long Metadata Game'))
        # Should NOT be created
        assert game is None
