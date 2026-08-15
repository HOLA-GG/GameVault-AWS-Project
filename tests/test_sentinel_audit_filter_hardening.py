"""Pruebas de regresión de seguridad para el filtrado de audit logs con límites de longitud."""

import pytest
import sys
import os


@pytest.fixture
def app_instance(monkeypatch):
    db_file = 'gamevault_test_audit_filter.db'
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


def test_obtener_todos_logs_truncates_overlong_filters(app_instance):
    """Verifica que filtros con strings más largos que los límites de esquema sean truncados y aplicados correctamente."""
    with app_instance.app_context():
        import app.models as models
        user_36 = "u" * 36
        models.crear_usuario(
            nombre="User 36",
            apellido="",
            email="user36@example.com",
            prefijo_pais="",
            telefono="",
            password_hash="hash123",
        )
        session_factory = models.get_session_factory()
        with session_factory() as session:
            u = session.query(models.User).filter_by(email="user36@example.com").first()
            u.user_id = user_36
            session.commit()

        # Crear logs con identificadores conocidos
        models.crear_log_audit(
            user_id=user_36,
            action="LOGIN",
            resource="auth",
            status="SUCCESS",
        )

        # 1. user_id filter con padding adicional
        overlong_user_id = user_36 + "EXTRA_PADDING_THAT_SHOULD_BE_TRUNCATED"
        logs = models.obtener_todos_logs({"user_id": overlong_user_id})
        assert len(logs) == 1
        assert logs[0]["user_id"] == user_36

        # 2. action filter con padding adicional
        action_80 = "A" * 80
        models.crear_log_audit(
            user_id=user_36,
            action=action_80,
            resource="test",
            status="SUCCESS",
        )
        overlong_action = action_80 + "_EXTRA_PADDING"
        logs_action = models.obtener_todos_logs({"action": overlong_action})
        assert len(logs_action) == 1
        assert logs_action[0]["action"] == action_80

        # 3. status filter con padding adicional
        status_20 = "S" * 20
        models.crear_log_audit(
            user_id=user_36,
            action="CUSTOM_ACTION",
            resource="test",
            status=status_20,
        )
        overlong_status = status_20 + "_EXTRA_PADDING"
        logs_status = models.obtener_todos_logs({"status": overlong_status})
        assert len(logs_status) == 1
        assert logs_status[0]["status"] == status_20
