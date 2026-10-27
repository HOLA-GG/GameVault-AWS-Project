"""Pruebas de integridad para acciones de auditoría y mapeo de insignias visuales."""

import os
import re
import pytest
from app import create_app
from app.models import AUDIT_ACTIONS, crear_log_audit, obtener_todos_logs
from app.routes import _ACTION_BADGE_MAP, ACTION_BADGE_GROUPS, get_action_badge_class


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_audit_completeness.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    import app.models as models
    models.DATABASE_URL = f'sqlite+pysqlite:///{db_file}'
    models._engine = None
    models._session_factory = None
    models._database_initialized = False

    flask_app = create_app()
    flask_app.config['TESTING'] = True

    with flask_app.app_context():
        models.init_database()
        yield flask_app

    models._engine = None
    models._session_factory = None
    models._database_initialized = False

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass


def test_all_route_audit_actions_registered():
    """Verifica que todas las acciones usadas en crear_log_audit estén registradas en AUDIT_ACTIONS."""
    with open('app/routes.py', 'r', encoding='utf-8') as f:
        routes_code = f.read()

    # Extrapolar los valores literales pasados como action='...'
    action_matches = set(re.findall(r"action=['\"]([^'\"]+)['\"]", routes_code))

    for action in action_matches:
        assert action in AUDIT_ACTIONS, f"Acción de auditoría '{action}' encontrada en app/routes.py pero no registrada en AUDIT_ACTIONS"


def test_all_audit_actions_categorized_in_badge_groups():
    """Verifica que todas las acciones registradas en AUDIT_ACTIONS tengan grupo de badge en ACTION_BADGE_GROUPS."""
    all_grouped_actions = set()
    for actions in ACTION_BADGE_GROUPS.values():
        all_grouped_actions.update(actions)

    for action in AUDIT_ACTIONS.keys():
        assert action in all_grouped_actions, f"Acción de auditoría '{action}' en AUDIT_ACTIONS no está asignada a ningún grupo en ACTION_BADGE_GROUPS"


def test_action_badge_class_resolution(app):
    """Verifica el mapeo O(1) de clases de badge para acciones conocidas y no conocidas."""
    assert get_action_badge_class('LOGIN') == 'action-auth'
    assert get_action_badge_class('CREATE_GAME') == 'action-games'
    assert get_action_badge_class('REGISTER') == 'action-users'
    assert get_action_badge_class('ADMIN_ACTION') == 'action-admin'
    assert get_action_badge_class('PRESIGNED_UPLOAD_FAILED') == 'action-admin'
    assert get_action_badge_class('UNKNOWN_CUSTOM_ACTION') == 'action-generic'


def test_audit_log_derived_name_generation(app):
    """Verifica que crear_log_audit utilice el nombre traducido derivado de AUDIT_ACTIONS."""
    with app.app_context():
        res = crear_log_audit(
            user_id='test-user-123',
            action='PRESIGNED_UPLOAD_FAILED',
            resource='storage',
            details={'reason': 'test'},
            status='FAILED',
        )
        assert res['success'] is True

        logs = obtener_todos_logs({'action': 'PRESIGNED_UPLOAD_FAILED'})
        assert len(logs) > 0
        log = logs[0]
        assert log['action_name'] == 'Fallo de carga firmada'
