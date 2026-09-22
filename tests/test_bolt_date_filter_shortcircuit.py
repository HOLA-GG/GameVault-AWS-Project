"""Unit tests for Bolt date filter short-circuit optimization in audit logs."""

from datetime import datetime, timezone
from app.__init__ import create_app
from app.models import obtener_todos_logs, crear_log_audit, ensure_tables, get_session_factory, AuditLog
from sqlalchemy import delete


def test_obtener_todos_logs_date_filter_shortcircuit():
    """Verifies that date filter short-circuiting returns correct log subsets for empty, valid, and invalid dates."""
    app = create_app()
    with app.app_context():
        ensure_tables()
        session_factory = get_session_factory()
        with session_factory() as session:
            session.execute(delete(AuditLog))
            session.commit()

        # Create logs
        crear_log_audit(user_id='u1', action='LOGIN', resource='auth', status='SUCCESS')
        crear_log_audit(user_id='u2', action='REGISTER', resource='users', status='SUCCESS')

        # Test 1: Empty filters (short-circuit path)
        logs_all = obtener_todos_logs({})
        assert len(logs_all) == 2

        # Test 2: Valid start_date filter
        logs_filtered = obtener_todos_logs({'start_date': '2000-01-01'})
        assert len(logs_filtered) == 2

        # Test 3: Future start_date filter
        logs_future = obtener_todos_logs({'start_date': '2099-01-01'})
        assert len(logs_future) == 0

        # Test 4: None / Empty string filters explicitly
        logs_empty_str = obtener_todos_logs({'start_date': '', 'end_date': ''})
        assert len(logs_empty_str) == 2
