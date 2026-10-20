import pytest
import os
import sys
import hashlib
from unittest.mock import patch
from werkzeug.security import generate_password_hash
from sqlalchemy import select


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_game_exception.db'
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


def test_agregar_juego_route_unexpected_exception(client, app):
    """Verifica que una excepción no controlada en /agregar capture la excepción y registre log FAILED."""
    from app.models import get_session_factory, AuditLog, crear_usuario

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Exception",
        apellido="Tester",
        email="game_exception_add@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw,
    )
    assert user is not None

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    with patch('app.routes.crear_juego', side_effect=Exception('Simulated unexpected crash during game creation')):
        response = client.post(
            '/agregar',
            data={
                'titulo': 'Unexpected Crash Game',
                'descripcion': 'Description',
                'plataforma': 'PC',
                'estado': 'Nuevo',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'CREATE_GAME',
                AuditLog.status == 'FAILED',
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'


def test_eliminar_juego_route_unexpected_exception(client, app):
    """Verifica que una excepción no controlada en /delete/<game_id> capture la excepción y registre log FAILED."""
    from app.models import get_session_factory, AuditLog, crear_usuario, crear_juego

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Exception",
        apellido="Tester",
        email="game_exception_del@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw,
    )
    assert user is not None

    game_id = "test-game-del-crash"
    crear_juego(user['user_id'], game_id, "Crash Game", "Desc", None, "PC", "Nuevo", "Biblioteca", "Media", 8, False)

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    with patch('app.routes.eliminar_juego', side_effect=Exception('Simulated unexpected crash during deletion')):
        response = client.post(
            f'/delete/{game_id}',
            follow_redirects=True,
        )
        assert response.status_code == 200

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'DELETE_GAME',
                AuditLog.status == 'FAILED',
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'


def test_editar_juego_route_unexpected_exception(client, app):
    """Verifica que una excepción no controlada en /edit/<game_id> capture la excepción y registre log FAILED."""
    from app.models import get_session_factory, AuditLog, crear_usuario, crear_juego

    pw = generate_password_hash("GameUserPass1!")
    user = crear_usuario(
        nombre="Game Exception",
        apellido="Tester",
        email="game_exception_edit@example.com",
        prefijo_pais="",
        telefono="",
        password_hash=pw,
    )
    assert user is not None

    game_id = "test-game-edit-crash"
    crear_juego(user['user_id'], game_id, "Crash Game Edit", "Desc", None, "PC", "Nuevo", "Biblioteca", "Media", 8, False)

    with client.session_transaction() as sess:
        sess['user_id'] = user['user_id']
        sess['email'] = user['email']
        sess['nombre'] = user['nombre']
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw.encode('utf-8')).hexdigest()

    with patch('app.routes.actualizar_juego', side_effect=Exception('Simulated unexpected crash during update')):
        response = client.post(
            f'/edit/{game_id}',
            data={
                'titulo': 'Updated Fail Title',
                'descripcion': 'Updated description',
                'plataforma': 'PC',
                'estado': 'Nuevo',
            },
            follow_redirects=True,
        )
        assert response.status_code == 200

    session_factory = get_session_factory()
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(
                AuditLog.user_id == user['user_id'],
                AuditLog.action == 'UPDATE_GAME',
                AuditLog.status == 'FAILED',
            )
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('reason') == 'exception_raised'
