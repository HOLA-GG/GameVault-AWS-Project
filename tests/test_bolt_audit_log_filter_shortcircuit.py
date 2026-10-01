"""
tests/test_bolt_audit_log_filter_shortcircuit.py - Test short-circuit evaluation for audit log filters.
"""

import os
import sys
import pytest


@pytest.fixture
def app_instance(monkeypatch):
    db_file = 'gamevault_test_audit_bolt.db'
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
        import app.models as models_module
        models_module.init_database()
        yield flask_app

    if os.path.exists(db_file):
        os.remove(db_file)


def test_obtener_todos_logs_empty_and_active_filters(app_instance):
    """Verify that empty, None, whitespace, and active filter parameters execute as expected."""
    with app_instance.app_context():
        import app.models as models

        u = models.crear_usuario(
            nombre="Bolt User",
            apellido="",
            email="bolt_user@example.com",
            prefijo_pais="",
            telefono="",
            password_hash="hash123",
        )
        user_id = u['user_id']

        # Create a log entry
        models.crear_log_audit(
            user_id=user_id,
            action="LOGIN",
            resource="auth",
            status="SUCCESS",
        )

        # 1. Test with None / empty dict
        res1 = models.obtener_todos_logs(None)
        assert len(res1) == 1

        res2 = models.obtener_todos_logs({})
        assert len(res2) == 1

        # 2. Test with empty string filter parameters (default from request.args)
        res3 = models.obtener_todos_logs({'user_id': '', 'action': '', 'status': ''})
        assert len(res3) == 1

        # 3. Test with None parameter values in filter dict
        res4 = models.obtener_todos_logs({'user_id': None, 'action': None, 'status': None})
        assert len(res4) == 1

        # 4. Test with matching active filters
        res5 = models.obtener_todos_logs({'user_id': user_id, 'action': 'LOGIN', 'status': 'SUCCESS'})
        assert len(res5) == 1
        assert res5[0]['user_id'] == user_id

        # 5. Test with non-matching active filters
        res6 = models.obtener_todos_logs({'user_id': 'nonexistent-user'})
        assert len(res6) == 0
