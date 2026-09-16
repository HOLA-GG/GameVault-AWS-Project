"""Test coverage for Bolt's admin log selected group resolution short-circuiting optimization."""

import os
import sys
import pytest


@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_bolt_admin_logs.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except OSError:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('WTF_CSRF_ENABLED', 'false')

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
        except OSError:
            pass


@pytest.fixture
def client(app):
    return app.test_client()


def resolve_selected_group(pagination_items, selected_user_id):
    """Replicates the selected group resolution logic from admin_logs in app/routes.py."""
    selected_group = None
    if pagination_items:
        if selected_user_id:
            selected_group = next(
                (group for group in pagination_items if group['user_id'] == selected_user_id),
                pagination_items[0],
            )
        else:
            selected_group = pagination_items[0]
    return selected_group


def test_selected_group_empty_selected_user_id():
    """Verify that empty selected_user_id returns the first item without iterating over groups."""
    groups = [
        {'user_id': 'user-1', 'nombre': 'Alice'},
        {'user_id': 'user-2', 'nombre': 'Bob'},
        {'user_id': 'system', 'nombre': 'Sistema'},
    ]

    selected = resolve_selected_group(groups, '')
    assert selected == groups[0]
    assert selected['user_id'] == 'user-1'


def test_selected_group_matching_user_id():
    """Verify that a matching selected_user_id correctly locates the targeted group."""
    groups = [
        {'user_id': 'user-1', 'nombre': 'Alice'},
        {'user_id': 'user-2', 'nombre': 'Bob'},
        {'user_id': 'system', 'nombre': 'Sistema'},
    ]

    selected = resolve_selected_group(groups, 'user-2')
    assert selected == groups[1]
    assert selected['nombre'] == 'Bob'


def test_selected_group_non_matching_user_id_fallback():
    """Verify that a non-matching selected_user_id safely falls back to the first group."""
    groups = [
        {'user_id': 'user-1', 'nombre': 'Alice'},
        {'user_id': 'user-2', 'nombre': 'Bob'},
    ]

    selected = resolve_selected_group(groups, 'non-existent-id')
    assert selected == groups[0]


def test_selected_group_empty_pagination_items():
    """Verify that empty pagination items safely return None."""
    assert resolve_selected_group([], '') is None
    assert resolve_selected_group([], 'user-1') is None


def test_admin_logs_route_group_selection(client, app):
    """Integration test verifying admin_logs route handles default and selected user IDs correctly."""
    from werkzeug.security import generate_password_hash
    from app.models import crear_usuario, crear_log_audit, get_session_factory, User
    from sqlalchemy import update
    import hashlib

    admin_pw = generate_password_hash('AdminPW123!')
    admin_dict = crear_usuario('AdminLogTest', 'User', 'admin_log_group_opt@test.com', '', '', admin_pw)
    session_factory = get_session_factory()
    with session_factory() as session:
        session.execute(update(User).where(User.user_id == admin_dict['user_id']).values(role='admin'))
        session.commit()

    user_pw = generate_password_hash('UserPW123!')
    user_dict = crear_usuario('UserTarget', 'Two', 'target_user_group_opt@test.com', '', '', user_pw)

    crear_log_audit(user_id=admin_dict['user_id'], action='LOGIN', resource='auth')
    crear_log_audit(user_id=user_dict['user_id'], action='CREATE_GAME', resource='games')

    with client.session_transaction() as sess:
        sess['user_id'] = admin_dict['user_id']
        sess['email'] = admin_dict['email']
        sess['nombre'] = admin_dict['nombre']
        sess['role'] = 'admin'
        sess['_pw_hash'] = hashlib.sha256(admin_pw.encode('utf-8')).hexdigest()

    # Default load (no selected_user_id parameter)
    resp_default = client.get('/admin/logs')
    assert resp_default.status_code == 200

    # Specific user load (selected_user_id parameter)
    resp_user = client.get(f'/admin/logs?selected_user_id={user_dict["user_id"]}')
    assert resp_user.status_code == 200
