import hashlib
import os
import sys
import pytest


@pytest.fixture
def admin_client(monkeypatch):
    db_file = 'gamevault_test_admin_logs_page.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

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

    with flask_app.app_context():
        import app.models as models
        models.init_database()
        pw_hash = "scrypt:32768:8:1$I5M8muL7dw4n9QXZ$e6f7a505f876cee29b89fd0fb1fd13f8be1ac953c9b6dea87709cb9cd105c8525ad2854e1400b5de5e36b405c189a247bf212008e6259277e98a71392edcd920"
        admin = models.crear_usuario(
            nombre="Admin Test",
            apellido="",
            email="admin_page@example.com",
            prefijo_pais="",
            telefono="",
            password_hash=pw_hash,
        )
        session_factory = models.get_session_factory()
        with session_factory() as session:
            u = session.query(models.User).filter_by(email="admin_page@example.com").first()
            u.role = "admin"
            session.commit()

        client = flask_app.test_client()
        pw_hash_gen = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()
        with client.session_transaction() as sess:
            sess["user_id"] = admin["user_id"]
            sess["email"] = "admin_page@example.com"
            sess["nombre"] = "Admin Test"
            sess["role"] = "admin"
            sess["_pw_hash"] = pw_hash_gen

        yield client

    if os.path.exists(db_file):
        os.remove(db_file)


def test_admin_logs_page_bounds(admin_client):
    """Test that oversized, negative, or invalid page query parameters on /admin/logs parse safely without crashing."""
    # Test 1: Oversized integer string (e.g. integer overflow)
    response = admin_client.get('/admin/logs?page=999999999999999999999999999999')
    assert response.status_code == 200

    # Test 2: Negative page number
    response = admin_client.get('/admin/logs?page=-10')
    assert response.status_code == 200

    # Test 3: Non-numeric invalid page value
    response = admin_client.get('/admin/logs?page=invalid')
    assert response.status_code == 200

    # Test 4: Page value = 0
    response = admin_client.get('/admin/logs?page=0')
    assert response.status_code == 200
