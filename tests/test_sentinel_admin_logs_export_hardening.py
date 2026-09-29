import os
import sys
import uuid
import hashlib
import pytest
from unittest.mock import patch
from sqlalchemy import select


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_export_hardening.db'
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
        except Exception:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


def test_admin_logs_export_success(client, app):
    """Verifica la exportación exitosa de logs con auditoría SUCCESS."""
    from app.models import get_session_factory, User, AuditLog, generate_password_hash

    admin_id = str(uuid.uuid4())
    pw_hash = generate_password_hash('AdminSecret123!')

    session_factory = get_session_factory()
    with session_factory() as db_session:
        admin = User(
            user_id=admin_id,
            email='admin_export_succ@sentinel.com',
            nombre='AdminExport',
            password_hash=pw_hash,
            role='admin',
            status='active'
        )
        db_session.add(admin)
        db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['email'] = 'admin_export_succ@sentinel.com'
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    response = client.get('/admin/logs/export')
    assert response.status_code == 200
    assert response.mimetype == 'text/csv'

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_id, AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'SUCCESS')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'export_logs'


def test_admin_logs_export_failure_audited(client, app):
    """Verifica que si ocurre una excepción durante la exportación de logs se registre auditoría FAILED y se redirija de forma segura."""
    from app.models import get_session_factory, User, AuditLog, generate_password_hash

    admin_id = str(uuid.uuid4())
    pw_hash = generate_password_hash('AdminSecret123!')

    session_factory = get_session_factory()
    with session_factory() as db_session:
        admin = User(
            user_id=admin_id,
            email='admin_export_fail@sentinel.com',
            nombre='AdminFail',
            password_hash=pw_hash,
            role='admin',
            status='active'
        )
        db_session.add(admin)
        db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = admin_id
        sess['email'] = 'admin_export_fail@sentinel.com'
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # Simular un error inesperado al generar el CSV
    with patch('app.routes.exportar_logs_csv', side_effect=RuntimeError('Database disk I/O error')):
        response = client.get('/admin/logs/export', follow_redirects=True)
        assert response.status_code == 200
        assert b'No se pudieron exportar los logs de auditor' in response.data

    with session_factory() as session:
        log = session.scalar(
            select(AuditLog)
            .where(AuditLog.user_id == admin_id, AuditLog.action == 'ADMIN_ACTION', AuditLog.status == 'FAILED')
            .order_by(AuditLog.timestamp.desc())
        )
        assert log is not None
        assert log.details.get('operation') == 'export_logs'
        assert 'Database disk I/O error' in log.details.get('error', '')
