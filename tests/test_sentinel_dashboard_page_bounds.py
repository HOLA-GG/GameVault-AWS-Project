import pytest
import sys
import os

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_dashboard_page_bounds.db'
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


def test_dashboard_page_bounds_overflow(client, app):
    """Verifica que valores gigantescos o malformados de page en /dashboard no provoquen 500/OverflowError."""
    from app.models import crear_usuario
    from werkzeug.security import generate_password_hash
    import hashlib

    # Crear un usuario activo
    email = "user_page_bounds@example.com"
    pw_hash = generate_password_hash("ValidPass123!")
    res = crear_usuario("PageUser", "Test", email, "+52", "1234567890", pw_hash)
    assert res is not None
    user_id = res['user_id']

    # Autenticar vía sesión
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = email
        sess['nombre'] = "PageUser"
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # Probar con valor extremadamente grande (OverflowError)
    resp = client.get('/dashboard?page=99999999999999999999999999999999999999999999999')
    assert resp.status_code == 200

    # Probar con valor negativo
    resp_neg = client.get('/dashboard?page=-5')
    assert resp_neg.status_code == 200

    # Probar con valor no numérico que falle conversión
    resp_str = client.get('/dashboard?page=abc')
    assert resp_str.status_code == 200
