"""Pruebas de regresión de seguridad para truncamiento de parámetros de consulta en rutas administrativas."""

import os
import sys
import pytest


@pytest.fixture
def admin_client(monkeypatch):
    db_file = 'gamevault_test_admin_query_bounds.db'
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
        # Create admin user
        admin = models.crear_usuario(
            nombre="Admin Test",
            apellido="",
            email="admin_query@example.com",
            prefijo_pais="",
            telefono="",
            password_hash="scrypt:32768:8:1$I5M8muL7dw4n9QXZ$e6f7a505f876cee29b89fd0fb1fd13f8be1ac953c9b6dea87709cb9cd105c8525ad2854e1400b5de5e36b405c189a247bf212008e6259277e98a71392edcd920",
        )
        session_factory = models.get_session_factory()
        with session_factory() as session:
            u = session.query(models.User).filter_by(email="admin_query@example.com").first()
            u.role = "admin"
            session.commit()

        import hashlib
        client = flask_app.test_client()
        with client.session_transaction() as sess:
            sess['user_id'] = admin['user_id']
            sess['email'] = admin['email']
            sess['role'] = 'admin'
            sess['_pw_hash'] = hashlib.sha256(admin['password_hash'].encode('utf-8')).hexdigest()

        yield client, flask_app

    if os.path.exists(db_file):
        os.remove(db_file)


def test_admin_collections_query_truncation(admin_client):
    """Verifica que el parámetro 'visibility' excesivo en /admin/collections se me maneje sin errores."""
    client, app = admin_client
    oversized_vis = "public" + "x" * 1000
    res = client.get(f'/admin/collections?visibility={oversized_vis}')
    assert res.status_code == 200


def test_admin_logs_query_truncation(admin_client):
    """Verifica que los parámetros de filtrado en /admin/logs y /admin/logs/export se trunquen de forma segura."""
    client, app = admin_client
    oversized_user_id = "u" * 500
    oversized_action = "A" * 500
    oversized_status = "S" * 500
    oversized_date = "2026-01-01" + "D" * 500

    # GET /admin/logs
    res_logs = client.get(
        f'/admin/logs?user_id={oversized_user_id}&action={oversized_action}&status={oversized_status}&start_date={oversized_date}&end_date={oversized_date}&selected_user_id={oversized_user_id}'
    )
    assert res_logs.status_code == 200

    # GET /admin/logs/export
    res_export = client.get(
        f'/admin/logs/export?user_id={oversized_user_id}&action={oversized_action}&status={oversized_status}&start_date={oversized_date}&end_date={oversized_date}'
    )
    assert res_export.status_code == 200
    assert res_export.mimetype == 'text/csv'
