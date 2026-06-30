import pytest
import os
import sys
from pathlib import Path
import uuid

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'test_audit_persistence.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

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
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

def test_audit_log_retention_after_user_deletion(app):
    from app.models import crear_usuario, crear_log_audit, eliminar_usuario, obtener_todos_logs, get_session_factory, AuditLog, select, text

    with app.app_context():
        # 1. Create a user
        email = f"test_{uuid.uuid4()}@example.com"
        user_data = crear_usuario("Test User", "", email, "", "", "hashed_pw")
        user_id = user_data['user_id']

        # 2. Create an audit log for that user
        crear_log_audit(user_id, "PERSIST_TEST", "test_resource")

        # 3. Delete the user
        eliminar_usuario(user_id)

        # 4. Verify logs
        logs = obtener_todos_logs({'action': 'PERSIST_TEST'})
        assert len(logs) == 1, "Audit log should exist"

        # We need to check the raw model to see if user_id was set to NULL
        session = get_session_factory()()
        # Ensure FKs are ON for the check
        session.execute(text("PRAGMA foreign_keys=ON"))
        log_obj = session.scalar(select(AuditLog).where(AuditLog.action == "PERSIST_TEST"))

        assert log_obj is not None
        assert log_obj.user_id is None, f"Expected user_id to be NULL, but got {log_obj.user_id}"
        session.close()
