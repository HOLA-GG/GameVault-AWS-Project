import pytest
import uuid
import sys
import os
import hashlib
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_audit.db'
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

def test_admin_logs_export_audit_and_robots_tag(client, app):
    """Verifica que exportar logs genere auditoría y tenga X-Robots-Tag."""
    from app.models import get_session_factory, User, AuditLog, generate_password_hash

    # 1. Crear un admin
    pw_hash = generate_password_hash('SecurePass123!')
    admin_id = str(uuid.uuid4())
    session_factory = get_session_factory()
    with session_factory() as db_session:
        admin = User(
            user_id=admin_id,
            email='admin@sentinel.com',
            nombre='Admin',
            password_hash=pw_hash,
            role='admin',
            status='active'
        )
        db_session.add(admin)
        db_session.commit()

    # 2. Login
    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['email'] = 'admin@sentinel.com'
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Exportar logs
    response = client.get('/admin/logs/export?status=SUCCESS')
    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('text/csv')
    assert response.headers['X-Robots-Tag'] == 'noindex, nofollow'

    # 4. Verificar log de auditoría
    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_id, AuditLog.action == 'ADMIN_ACTION')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'export_logs'
        assert log.details.get('filters', {}).get('status') == 'SUCCESS'

def test_dashboard_has_robots_tag(client, app):
    """Verifica que el dashboard tenga X-Robots-Tag."""
    from app.models import get_session_factory, User, generate_password_hash

    # 1. Crear usuario
    pw_hash = generate_password_hash('SecurePass123!')
    user_id = str(uuid.uuid4())
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id=user_id,
            email='user@sentinel.com',
            nombre='User',
            password_hash=pw_hash,
            role='user',
            status='active'
        )
        db_session.add(user)
        db_session.commit()

    # 2. Login
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = 'user@sentinel.com'
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Acceder al dashboard
    response = client.get('/dashboard')
    assert response.status_code == 200
    assert response.headers['X-Robots-Tag'] == 'noindex, nofollow'
