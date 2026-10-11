"""Test short-circuiting behavior in obtener_todos_logs when filters is empty or contains date/status bounds."""

from app import create_app
from app.models import Base, AuditLog, User, get_engine, get_session_factory, obtener_todos_logs, utcnow


def test_obtener_todos_logs_shortcircuit_empty_and_populated_filters():
    """Verifica que obtener_todos_logs retorne resultados idénticos y correctos con filtros vacíos o con datos."""
    app = create_app()
    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        session_factory = get_session_factory()

        with session_factory() as session:
            session.query(AuditLog).delete()
            session.query(User).delete()
            session.commit()

            user1 = User(
                user_id='user-1',
                email='u1@test.com',
                nombre='User One',
                password_hash='hash1',
            )
            user2 = User(
                user_id='user-2',
                email='u2@test.com',
                nombre='User Two',
                password_hash='hash2',
            )
            session.add_all([user1, user2])
            session.commit()

            # Insert sample audit logs
            log1 = AuditLog(
                audit_id='log-test-1',
                user_id='user-1',
                action='LOGIN',
                action_name='Inicio de sesión',
                resource='auth',
                timestamp=utcnow(),
                ip_address='127.0.0.1',
                status='SUCCESS',
            )
            log2 = AuditLog(
                audit_id='log-test-2',
                user_id='user-2',
                action='UPDATE_PROFILE',
                action_name='Actualizar perfil',
                resource='users',
                timestamp=utcnow(),
                ip_address='127.0.0.1',
                status='FAILED',
            )
            session.add_all([log1, log2])
            session.commit()

        # Test with empty filters (None and dict)
        logs_none = obtener_todos_logs(None, limit=10, format_dates=False)
        logs_empty = obtener_todos_logs({}, limit=10, format_dates=False)

        assert len(logs_none) == 2
        assert len(logs_empty) == 2
        assert logs_none[0]['audit_id'] in {'log-test-1', 'log-test-2'}

        # Test with populated filters
        logs_filtered = obtener_todos_logs({'action': 'LOGIN'}, limit=10, format_dates=False)
        assert len(logs_filtered) == 1
        assert logs_filtered[0]['audit_id'] == 'log-test-1'

        logs_status = obtener_todos_logs({'status': 'FAILED'}, limit=10, format_dates=False)
        assert len(logs_status) == 1
        assert logs_status[0]['audit_id'] == 'log-test-2'
