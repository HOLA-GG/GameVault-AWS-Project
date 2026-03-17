from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def app(monkeypatch):
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


def test_dashboard_requires_login(client):
    response = client.get('/dashboard')

    assert response.status_code == 302
    assert '/login' in response.headers['Location']


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


def test_logout_is_post_only(client):
    login_session(client)

    response = client.get('/logout')

    assert response.status_code == 405


def test_presign_requires_auth(client):
    response = client.post('/api/uploads/presign', json={'filename': 'cover.png', 'content_type': 'image/png'})

    assert response.status_code == 302
    assert '/login' in response.headers['Location']
