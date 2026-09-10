import pytest
from app import create_app
from app.extensions import safe_get_remote_address


def test_safe_get_remote_address_cache_and_context():
    """Verifica que safe_get_remote_address use el puntero de función en caché y funcione en contextos de petición."""
    app = create_app()

    # Outside request context
    assert safe_get_remote_address() == '127.0.0.1'

    # Inside request context
    with app.test_request_context('/login', environ_base={'REMOTE_ADDR': '203.0.113.195'}):
        ip = safe_get_remote_address()
        assert ip == '203.0.113.195'

        # Verify cached function pointer is populated in function globals
        fn_cached = safe_get_remote_address.__globals__.get('_GET_REQUEST_IP_FN')
        assert fn_cached is not None

        # Verify second call reuses cached function pointer
        ip_second = safe_get_remote_address()
        assert ip_second == '203.0.113.195'
