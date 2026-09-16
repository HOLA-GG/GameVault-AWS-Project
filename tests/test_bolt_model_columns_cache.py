import uuid
import pytest
from app import create_app
from app.models import (
    User,
    AuditLog,
    _get_model_columns,
    _MODEL_COLUMNS_CACHE,
    obtener_todos_usuarios,
    obtener_usuarios_por_ids,
    obtener_logs_por_usuario,
    obtener_todos_logs,
    crear_usuario,
    crear_log_audit,
    init_database,
)


@pytest.fixture
def app_instance(monkeypatch, tmp_path):
    db_file = tmp_path / f"test_cols_{uuid.uuid4().hex[:8]}.db"
    monkeypatch.setenv("APP_ENV", "testing")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_file}")
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    app = create_app()
    with app.app_context():
        init_database()
        yield app


def test_get_model_columns_caching():
    """Verifica que _get_model_columns cachee las expresiones de columna por modelo y campos."""
    fields = ['user_id', 'email', 'nombre']

    cols1 = _get_model_columns(User, fields)
    cols2 = _get_model_columns(User, fields)
    cols3 = _get_model_columns(User, ('user_id', 'email', 'nombre'))

    assert cols1 is cols2
    assert cols1 is cols3
    assert len(cols1) == 3
    assert cols1[0] == User.user_id
    assert cols1[1] == User.email
    assert cols1[2] == User.nombre


def test_selective_projection_user_queries(app_instance):
    """Verifica que las consultas con proyecciones de User funcionen correctamente y usen la caché."""
    unique_email = f"col_{uuid.uuid4().hex[:8]}@example.com"
    u = crear_usuario('ColName', 'ColLastName', unique_email, '', '', 'hash123')
    assert u is not None

    user_id = u['user_id']

    # Test obtener_todos_usuarios with selective fields
    users = obtener_todos_usuarios(limit=10, fields=['user_id', 'email', 'nombre'])
    assert len(users) >= 1
    found = next((user for user in users if user['user_id'] == user_id), None)
    assert found is not None
    assert found['email'] == unique_email
    assert found['nombre'] == 'ColName'

    # Test obtener_usuarios_por_ids with selective fields
    users_by_ids = obtener_usuarios_por_ids([user_id], fields=['user_id', 'email', 'nombre'])
    assert len(users_by_ids) == 1
    assert users_by_ids[0]['user_id'] == user_id
    assert users_by_ids[0]['email'] == unique_email

    # Ensure (User, ('user_id', 'email', 'nombre')) is in cache
    key = (User, ('user_id', 'email', 'nombre'))
    assert key in _MODEL_COLUMNS_CACHE


def test_selective_projection_audit_log_queries(app_instance):
    """Verifica que las consultas con proyecciones de AuditLog funcionen correctamente y usen la caché."""
    unique_email = f"audit_col_{uuid.uuid4().hex[:8]}@example.com"
    u = crear_usuario('AuditColName', 'LastName', unique_email, '', '', 'hash456')
    assert u is not None
    user_id = u['user_id']

    crear_log_audit(
        user_id=user_id,
        action='LOGIN',
        resource='auth',
        details={'test': True},
        status='SUCCESS',
    )

    # Test obtener_logs_por_usuario with selective fields
    logs_by_user = obtener_logs_por_usuario(
        user_id,
        limit=5,
        fields=['audit_id', 'user_id', 'action', 'timestamp', 'status']
    )
    assert len(logs_by_user) >= 1
    assert logs_by_user[0]['action'] == 'LOGIN'
    assert logs_by_user[0]['status'] == 'SUCCESS'

    # Test obtener_todos_logs with selective fields
    all_logs = obtener_todos_logs(
        filters={'user_id': user_id},
        limit=5,
        fields=['audit_id', 'user_id', 'action', 'timestamp', 'status']
    )
    assert len(all_logs) >= 1
    assert all_logs[0]['action'] == 'LOGIN'

    # Ensure (AuditLog, ('audit_id', 'user_id', 'action', 'timestamp', 'status')) is in cache
    key = (AuditLog, ('audit_id', 'user_id', 'action', 'timestamp', 'status'))
    assert key in _MODEL_COLUMNS_CACHE
