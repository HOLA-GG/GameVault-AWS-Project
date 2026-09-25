import pytest
import os
import sys
from unittest.mock import patch
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_game_audit.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

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
        except Exception:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_game_creation_db_failure_audit_logged(client, app):
    """Verifica que el fallo al guardar un juego en DB registre un log de auditoría con status='FAILED'."""
    from app.models import get_session_factory, User, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Audit",
        apellido="Tester",
        email="game_audit_create@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw
    )
    assert user is not None

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    with patch('app.routes.crear_juego', return_value=None):
        response = client.post('/agregar', data={
            'titulo': 'Test Game Fail',
            'descripcion': 'Test description',
            'plataforma': 'PC',
            'estado': 'Nuevo',
            'categoria': 'Biblioteca',
            'prioridad': 'Media',
        })
        assert response.status_code == 302

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'CREATE_GAME',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'db_save_failed'
        assert log.details.get('title') == 'Test Game Fail'

def test_game_update_failure_audit_logged(client, app):
    """Verifica que el fallo al actualizar un juego registre un log de auditoría con status='FAILED'."""
    from app.models import get_session_factory, AuditLog, crear_usuario, crear_juego
    from werkzeug.security import generate_password_hash
    import hashlib

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Audit",
        apellido="Tester",
        email="game_audit_update@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw
    )
    assert user is not None

    game_id = "test-game-update-id"
    crear_juego(user['user_id'], game_id, "Original Title", "Original Desc", None, "PC", "Nuevo", "Biblioteca", "Media", 8, False)

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    with patch('app.routes.actualizar_juego', return_value={'success': False, 'error': 'DB constraint error'}):
        response = client.post(f'/edit/{game_id}', data={
            'titulo': 'Updated Fail Title',
            'descripcion': 'Updated description',
            'plataforma': 'PC',
            'estado': 'Nuevo',
            'categoria': 'Biblioteca',
            'prioridad': 'Media',
        })
        assert response.status_code == 302

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'UPDATE_GAME',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('game_id') == game_id
        assert log.details.get('reason') == 'db_update_failed'

def test_game_deletion_failure_audit_logged(client, app):
    """Verifica que el fallo al eliminar un juego registre un log de auditoría con status='FAILED'."""
    from app.models import get_session_factory, AuditLog, crear_usuario, crear_juego
    from werkzeug.security import generate_password_hash
    import hashlib

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Audit",
        apellido="Tester",
        email="game_audit_delete@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw
    )
    assert user is not None

    game_id = "test-game-delete-id"
    crear_juego(user['user_id'], game_id, "Game To Delete Fail", "Desc", None, "PC", "Nuevo", "Biblioteca", "Media", 8, False)

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    with patch('app.routes.eliminar_juego', return_value={'success': False, 'error': 'DB error during deletion'}):
        response = client.post(f'/delete/{game_id}')
        assert response.status_code == 302

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'DELETE_GAME',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('game_id') == game_id
        assert log.details.get('reason') == 'db_delete_failed'

def test_invalid_game_id_deletion_audit_logged(client, app):
    """Verifica que el intento de eliminar un juego con un ID inválido registre un log de auditoría FAILED."""
    from app.models import get_session_factory, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Audit Invalid",
        apellido="Tester",
        email="game_audit_invalid_del@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw
    )
    assert user is not None

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    invalid_game_id = "invalid_id_format_too_long_12345678901234567890"
    response = client.post(f'/delete/{invalid_game_id}')
    assert response.status_code == 302

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'DELETE_GAME',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'invalid_game_id'

def test_invalid_game_id_edit_audit_logged(client, app):
    """Verifica que el intento de editar un juego con un ID inválido registre un log de auditoría FAILED."""
    from app.models import get_session_factory, AuditLog, crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Audit Invalid Edit",
        apellido="Tester",
        email="game_audit_invalid_edit@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw
    )
    assert user is not None

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    invalid_game_id = "invalid_id_format_too_long_12345678901234567890"
    response = client.post(f'/edit/{invalid_game_id}', data={
        'titulo': 'Should Fail',
        'descripcion': 'Should Fail Desc',
        'plataforma': 'PC',
        'estado': 'Nuevo'
    })
    assert response.status_code == 302

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'UPDATE_GAME',
                AuditLog.status == 'FAILED'
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'invalid_game_id'
