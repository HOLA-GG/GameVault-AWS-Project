from __future__ import annotations

import importlib
from io import BytesIO
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
    db_path = PROJECT_ROOT / 'gamevault_test.db'
    if db_path.exists():
        db_path.unlink()

    env = {
        'APP_ENV': 'testing',
        'SECRET_KEY': 'test-secret-key',
        'AWS_REGION': 'us-east-1',
        'DATABASE_URL': 'sqlite+pysqlite:///gamevault_test.db',
        'S3_BUCKET_NAME': 'gamevault-test-bucket',
        'DYNAMODB_TABLE': 'GameVaultTest',
        'DYNAMODB_USERS_TABLE': 'GameVaultUsersTest',
        'DYNAMODB_RESET_TABLE': 'GameVaultPasswordResetTest',
        'DYNAMODB_AUDIT_TABLE': 'GameVaultAuditLogsTest',
        'STORAGE_BACKEND': 'none',
        'MAIL_SUPPRESS_SEND': 'true',
        'WTF_CSRF_ENABLED': 'false',
        'SESSION_COOKIE_SECURE': 'false',
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    app_module = importlib.import_module('app')
    flask_app = app_module.create_app()
    flask_app.config.update(TESTING=True, WTF_CSRF_ENABLED=False, MAIL_SUPPRESS_SEND=True)
    return flask_app


@pytest.fixture
def client(app):
    return app.test_client()


def login_session(client, *, role='user'):
    with client.session_transaction() as session:
        session['user_id'] = 'user-1'
        session['email'] = 'user@example.com'
        session['nombre'] = 'Tester'
        session['role'] = role


def test_healthz_returns_ok(client):
    response = client.get('/healthz')

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['status'] == 'ok'
    assert payload['app'] == 'GameVault'


def test_landing_renders_showcase_demo(client):
    response = client.get('/')

    assert response.status_code == 200
    assert b'Explora c' in response.data
    assert b'Valorar colecci' in response.data
    assert b'votos' in response.data


def test_showcase_rating_allows_one_vote_per_ip(client):
    response = client.post(
        '/api/showcase/rate',
        json={
            'subject_type': 'sample',
            'subject_id': 'demo-nintendo-reliquias',
            'rating': 4,
        },
        environ_base={'REMOTE_ADDR': '10.10.10.10'},
    )

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['success'] is True
    assert payload['votes_count'] >= 1
    assert payload['average'] is not None


def test_showcase_rating_blocks_duplicate_ip_for_same_collection(client):
    payload = {
        'subject_type': 'sample',
        'subject_id': 'demo-jrpg-esenciales',
        'rating': 5,
    }

    first_response = client.post(
        '/api/showcase/rate',
        json=payload,
        environ_base={'REMOTE_ADDR': '10.10.10.11'},
    )
    second_response = client.post(
        '/api/showcase/rate',
        json=payload,
        environ_base={'REMOTE_ADDR': '10.10.10.11'},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 409
    duplicate_payload = second_response.get_json()
    assert duplicate_payload['duplicate'] is True
    assert b'ya valor' in second_response.data


def test_dashboard_requires_login(client):
    response = client.get('/dashboard')

    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_dashboard_redirects_admin_to_admin_panel(client):
    login_session(client, role='admin')

    response = client.get('/dashboard')

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/admin')


def test_dashboard_renders_games(monkeypatch, client):
    import app.routes as routes

    monkeypatch.setattr(
        routes,
        'obtener_juegos_por_usuario',
        lambda _user_id: [
            {
                'game_id': 'g1',
                'titulo': 'Zelda',
                'descripcion': 'Aventura',
                'plataforma': 'Switch',
                'estado': 'Completado',
                'imagen_url': 'https://example.com/zelda.jpg',
                'created_at': '2026-03-01T00:00:00+00:00',
                'updated_at': '2026-03-02T00:00:00+00:00',
            }
        ],
    )
    monkeypatch.setattr(routes, 'crear_url_firmada_lectura', lambda image_url: image_url)
    login_session(client)

    response = client.get('/dashboard')

    assert response.status_code == 200
    assert b'Zelda' in response.data
    assert b'Switch' in response.data


def test_registration_redirects_to_dashboard(monkeypatch, client):
    import app.routes as routes

    monkeypatch.setattr(routes, 'obtener_usuario_por_email', lambda _email: None)
    monkeypatch.setattr(
        routes,
        'crear_usuario',
        lambda nombre, apellido, email, prefijo_pais, telefono, password_hash: {
            'user_id': 'new-user',
            'email': email,
            'nombre': nombre,
            'role': 'user',
        },
    )
    monkeypatch.setattr(routes, 'crear_log_audit', lambda **_kwargs: {'success': True})

    response = client.post(
        '/registro',
        data={
            'nombre': 'Ana',
            'email': 'ana@example.com',
            'password': 'password123',
            'confirm_password': 'password123',
        },
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/dashboard')


def test_forgot_password_never_exposes_token(monkeypatch, client):
    import app.routes as routes

    monkeypatch.setattr(routes, 'obtener_usuario_por_email', lambda _email: {'user_id': 'user-1'})
    monkeypatch.setattr(
        routes,
        'crear_reset_token',
        lambda _user_id, _ip: {
            'success': True,
            'token': 'super-secret-reset-token',
            'error': None,
        },
    )
    monkeypatch.setattr(routes, 'enviar_email_reset_password', lambda _email, _token: True)
    monkeypatch.setattr(routes, 'crear_log_audit', lambda **_kwargs: {'success': True})

    response = client.post(
        '/forgot-password',
        data={'email': 'ana@example.com'},
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Si el correo est' in response.data
    assert b'super-secret-reset-token' not in response.data


def test_forgot_password_can_show_debug_token_locally(monkeypatch, client):
    import app.routes as routes

    client.application.config['SHOW_RESET_DEBUG_TOKEN'] = True
    monkeypatch.setattr(routes, 'obtener_usuario_por_email', lambda _email: {'user_id': 'user-1'})
    monkeypatch.setattr(
        routes,
        'crear_reset_token',
        lambda _user_id, _ip: {
            'success': True,
            'token': 'local-debug-token',
            'expires_at': '2030-01-01T00:00:00+00:00',
            'error': None,
        },
    )
    monkeypatch.setattr(routes, 'enviar_email_reset_password', lambda _email, _token: False)
    monkeypatch.setattr(routes, 'crear_log_audit', lambda **_kwargs: {'success': True})

    response = client.post('/forgot-password', data={'email': 'ana@example.com'})

    assert response.status_code == 200
    assert b'local-debug-token' in response.data
    assert b'Recuperaci' in response.data


def test_logout_is_post_only(client):
    login_session(client)

    response = client.get('/logout')

    assert response.status_code == 405


def test_presign_requires_auth(client):
    response = client.post('/api/uploads/presign', json={'filename': 'cover.png', 'content_type': 'image/png'})

    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_add_game_supports_local_storage(client, tmp_path):
    client.application.config.update(
        STORAGE_BACKEND='local',
        LOCAL_UPLOAD_DIR=str(tmp_path),
        LOCAL_UPLOAD_URL_PATH='/static/uploads',
        DIRECT_UPLOADS_ENABLED=False,
    )
    login_session(client)

    response = client.post(
        '/agregar',
        data={
            'titulo': 'Metroid Prime',
            'descripcion': 'Edicion especial',
            'plataforma': 'Nintendo',
            'estado': 'Nuevo',
            'categoria': 'Wishlist',
            'prioridad': 'Alta',
            'calificacion': '9',
            'es_favorito': 'on',
            'imagen': (BytesIO(b'\x89PNG\r\n\x1a\nlocal-image'), 'cover.png', 'image/png'),
        },
        content_type='multipart/form-data',
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b'Metroid Prime' in response.data
    assert b'Wishlist' in response.data
    assert b'Favorito' in response.data
    assert list(tmp_path.rglob('*.png'))


def test_admin_logs_groups_entries_by_account(monkeypatch, client):
    import app.routes as routes

    monkeypatch.setattr(
        routes,
        'obtener_todos_logs',
        lambda _filters, limit=300: [
            {
                'audit_id': 'a1',
                'user_id': 'user-1',
                'action': 'LOGIN',
                'action_name': 'Inicio de sesión',
                'resource': 'auth',
                'timestamp': '2026-03-18T10:00:00+00:00',
                'status': 'SUCCESS',
                'ip_address': '127.0.0.1',
            },
            {
                'audit_id': 'a2',
                'user_id': 'user-2',
                'action': 'CREATE_GAME',
                'action_name': 'Crear juego',
                'resource': 'games',
                'timestamp': '2026-03-18T10:05:00+00:00',
                'status': 'SUCCESS',
                'ip_address': '127.0.0.2',
            },
        ],
    )
    monkeypatch.setattr(
        routes,
        'obtener_estadisticas_logs',
        lambda: {'total_logs': 2, 'success_rate': 100, 'top_users': ['user-1', 'user-2']},
    )
    monkeypatch.setattr(
        routes,
        'obtener_usuario_por_id',
        lambda user_id: {
            'user_id': user_id,
            'nombre': 'Ana' if user_id == 'user-1' else 'Luis',
            'email': f'{user_id}@example.com',
        },
    )
    login_session(client, role='admin')

    response = client.get('/admin/logs')

    assert response.status_code == 200
    assert b'user-1@example.com' in response.data
    assert b'user-2@example.com' in response.data
    assert b'Inicio de sesi' in response.data
    assert b'Crear juego' in response.data


def test_admin_navigation_is_visible_on_landing(client):
    login_session(client, role='admin')

    response = client.get('/')

    assert response.status_code == 200
    assert b'Panel admin' in response.data
    assert b'Colecciones' in response.data
    assert b'Logs' in response.data
    assert b'Mi colecci' not in response.data


def test_admin_panel_has_clear_return_paths(client):
    login_session(client, role='admin')

    response = client.get('/admin')

    assert response.status_code == 200
    assert b'Inicio' in response.data
    assert b'Usuarios' in response.data
    assert b'Colecciones' in response.data
    assert b'Logs' in response.data
    assert b'Mi colecci' not in response.data
    assert b'Perfil' not in response.data


def test_admin_collections_route_renders(client):
    login_session(client, role='admin')

    response = client.get('/admin/collections')

    assert response.status_code == 200
    assert b'Colecciones' in response.data
