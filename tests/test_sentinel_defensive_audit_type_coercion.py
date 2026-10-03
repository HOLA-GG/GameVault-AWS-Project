"""Tests for defensive parameter type coercion in audit logging and redirect length bounding."""

import pytest
from app import create_app
from app.models import AuditLog, crear_log_audit, get_session_factory
from sqlalchemy import select


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_crear_log_audit_defensive_type_coercion(app):
    """Verifies that crear_log_audit accepts non-string arguments without raising TypeError."""
    with app.app_context():
        # Pass non-string arguments: integers for action, resource, status, user_agent
        result = crear_log_audit(
            user_id='test-coercion-user',
            action=500,
            resource=404,
            status=500,
            user_agent=12345,
            details={'test': True},
        )
        assert result['success'] is True
        assert result['audit_id'] is not None

        session_factory = get_session_factory()
        with session_factory() as session:
            log = session.scalar(select(AuditLog).where(AuditLog.audit_id == result['audit_id']))
            assert log is not None
            assert log.action == '500'
            assert log.resource == '404'
            assert log.status == '500'
            assert log.user_agent == '12345'


def test_require_login_redirect_length_bounding(client):
    """Verifies that require_login truncates oversized URL targets in the next redirect parameter."""
    long_query = 'a' * 5000
    response = client.get(f'/dashboard?long_param={long_query}', follow_redirects=False)
    assert response.status_code == 302
    location = response.headers.get('Location', '')
    assert location.startswith('/login?next=')
    # The next parameter value should be bounded and not exceed 2048 chars
    assert len(location) < 3000
