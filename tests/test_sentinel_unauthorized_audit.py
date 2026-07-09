import pytest
import sys
import os
import hashlib
from pathlib import Path
from flask import session

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_unauthorized_audit.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

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

def test_audit_unauthorized_edit_game(client):
    from app.models import get_session_factory, User, Game, AuditLog, select

    # 1. Create two users and a game for user 1
    pw_hash = "fake_hash"
    session_factory = get_session_factory()
    with session_factory() as db_session:
        u1 = User(user_id='u1', email='u1@example.com', nombre='U1', password_hash=pw_hash)
        u2 = User(user_id='u2', email='u2@example.com', nombre='U2', password_hash=pw_hash)
        g1 = Game(game_id='g1', user_id='u1', titulo='Game 1', descripcion='Desc 1')
        db_session.add_all([u1, u2, g1])
        db_session.commit()

    # 2. Login as user 2
    with client.session_transaction() as sess:
        sess['user_id'] = 'u2'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Attempt to edit user 1's game
    response = client.post('/edit/g1', data={'titulo': 'Hack'}, follow_redirects=True)
    assert b'Juego no encontrado o sin permisos.' in response.data

    # 4. Verify audit log
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'u2',
                AuditLog.action == 'UNAUTHORIZED_ACCESS',
                AuditLog.details['game_id'].as_string() == 'g1',
                AuditLog.details['operation'].as_string() == 'edit_game'
            )
        )
        assert log is not None
        assert log.status == 'FAILED'

def test_audit_unauthorized_delete_game(client):
    from app.models import get_session_factory, User, Game, AuditLog, select

    # 1. Create two users and a game for user 1
    pw_hash = "fake_hash"
    session_factory = get_session_factory()
    with session_factory() as db_session:
        u1 = User(user_id='u1_d', email='u1_d@example.com', nombre='U1', password_hash=pw_hash)
        u2 = User(user_id='u2_d', email='u2_d@example.com', nombre='U2', password_hash=pw_hash)
        g1 = Game(game_id='g1_d', user_id='u1_d', titulo='Game 1', descripcion='Desc 1')
        db_session.add_all([u1, u2, g1])
        db_session.commit()

    # 2. Login as user 2
    with client.session_transaction() as sess:
        sess['user_id'] = 'u2_d'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Attempt to delete user 1's game
    response = client.post('/delete/g1_d', follow_redirects=True)
    assert b'Juego no encontrado o sin permisos.' in response.data

    # 4. Verify audit log
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'u2_d',
                AuditLog.action == 'UNAUTHORIZED_ACCESS',
                AuditLog.details['game_id'].as_string() == 'g1_d',
                AuditLog.details['operation'].as_string() == 'delete_game'
            )
        )
        assert log is not None
        assert log.status == 'FAILED'

def test_audit_validation_failure_create(client):
    from app.models import get_session_factory, User, AuditLog, select

    # 1. Create user
    pw_hash = "fake_hash"
    session_factory = get_session_factory()
    with session_factory() as db_session:
        u1 = User(user_id='u_v', email='u_v@example.com', nombre='UV', password_hash=pw_hash)
        db_session.add(u1)
        db_session.commit()

    # 2. Login
    with client.session_transaction() as sess:
        sess['user_id'] = 'u_v'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Attempt to create game with empty title
    response = client.post('/agregar', data={'titulo': '', 'descripcion': 'valid'}, follow_redirects=True)
    assert b'El t\xc3\xadtulo es requerido.' in response.data

    # 4. Verify audit log
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'u_v',
                AuditLog.action == 'CREATE_GAME',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert 'El título es requerido.' in log.details['errors']

def test_audit_validation_failure_edit(client):
    from app.models import get_session_factory, User, Game, AuditLog, select

    # 1. Create user and game
    pw_hash = "fake_hash"
    session_factory = get_session_factory()
    with session_factory() as db_session:
        u1 = User(user_id='u_ve', email='u_ve@example.com', nombre='UVE', password_hash=pw_hash)
        g1 = Game(game_id='g_ve', user_id='u_ve', titulo='Title', descripcion='Desc')
        db_session.add_all([u1, g1])
        db_session.commit()

    # 2. Login
    with client.session_transaction() as sess:
        sess['user_id'] = 'u_ve'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Attempt to edit with empty title
    response = client.post('/edit/g_ve', data={'titulo': '', 'descripcion': 'valid'}, follow_redirects=True)
    assert b'El t\xc3\xadtulo es requerido.' in response.data

    # 4. Verify audit log
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'u_ve',
                AuditLog.action == 'UPDATE_GAME',
                AuditLog.status == 'FAILED'
            )
        )
        assert log is not None
        assert 'El título es requerido.' in log.details['errors']

def test_audit_unsafe_redirect(client):
    from app.models import get_session_factory, User, AuditLog, select
    from werkzeug.security import generate_password_hash

    # 1. Create user
    pw = "SecurePass123!"
    pw_hash = generate_password_hash(pw)
    session_factory = get_session_factory()
    with session_factory() as db_session:
        u1 = User(user_id='u_red', email='u_red@example.com', nombre='URED', password_hash=pw_hash, status='active')
        db_session.add(u1)
        db_session.commit()

    # 2. Login with unsafe next
    response = client.post('/login?next=http://evil.com', data={
        'email': 'u_red@example.com',
        'password': pw
    }, follow_redirects=True)

    # 3. Should NOT redirect to evil.com
    assert response.status_code == 200
    assert b'evil.com' not in response.data

    # 4. Verify audit log
    with session_factory() as db_session:
        log = db_session.scalar(
            select(AuditLog).where(
                AuditLog.user_id == 'u_red',
                AuditLog.action == 'UNAUTHORIZED_ACCESS',
                AuditLog.details['reason'].as_string() == 'unsafe_redirect_intercepted'
            )
        )
        assert log is not None
        assert log.status == 'FAILED'
        assert 'http://evil.com' in log.details['next_url']
