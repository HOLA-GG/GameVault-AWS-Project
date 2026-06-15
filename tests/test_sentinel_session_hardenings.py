import hashlib
import pytest
import sys
import os
import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('WTF_CSRF_ENABLED', '0')

    # Force reload of app and models to ensure the new DATABASE_URL is used
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

def test_session_invalidation_logic(client):
    """Verifica que un cambio de contraseña invalide la sesión según el nuevo require_login."""
    from app.models import crear_usuario, actualizar_password_usuario
    from werkzeug.security import generate_password_hash

    # 1. Crear usuario
    email = "session-test@example.com"
    pw_old = "password123"
    pw_hash_old = generate_password_hash(pw_old)
    user = crear_usuario("Session", "Tester", email, "", "123456789", pw_hash_old)
    user_id = user['user_id']

    # 2. Simular login (inyectar en sesión con el hash SHA256 esperado)
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['_pw_hash'] = hashlib.sha256(pw_hash_old.encode('utf-8')).hexdigest()

    # 3. Verificar que tiene acceso
    response = client.get('/dashboard')
    assert response.status_code == 200

    # 4. Cambiar contraseña en DB
    pw_new = "newpassword456"
    pw_hash_new = generate_password_hash(pw_new)
    actualizar_password_usuario(user_id, pw_hash_new)

    # 5. Intentar acceder de nuevo (debería redirigir a login porque _pw_hash ya no coincide)
    response = client.get('/dashboard', follow_redirects=True)
    assert b'Tu sesi\xc3\xb3n ha sido invalidada por un cambio de seguridad' in response.data

    with client.session_transaction() as sess:
        assert 'user_id' not in sess

def test_admin_edit_user_name_length_validation(client):
    """Verifica que la edición de usuario por admin valide la longitud del nombre."""
    from app.models import ensure_bootstrap_admin, crear_usuario, obtener_usuario_por_id

    # Setup admin
    admin_email = "admin-val@gamevault"
    admin_pw = "admin123"
    ensure_bootstrap_admin(admin_email, admin_pw)

    # Login as admin
    client.post('/login', data={'email': admin_email, 'password': admin_pw})

    # Create a target user
    user = crear_usuario("Target", "User", "target@example.com", "", "12345678", "hash")
    user_id = user['user_id']

    # Attempt to rename with > 120 chars
    long_name = "A" * 121
    response = client.post(f'/admin/edit/{user_id}', data={'nombre': long_name}, follow_redirects=True)

    assert b'El nombre es demasiado largo' in response.data

    # Verify name hasn't changed
    updated_user = obtener_usuario_por_id(user_id)
    assert updated_user['nombre'] == "Target"
