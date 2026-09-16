"""Pruebas unitarias para la optimización por regex de is_safe_url en app/routes.py."""

from app import create_app
from app.routes import is_safe_url


def test_is_safe_url_regex_validation():
    """Verifica que is_safe_url valide correctamente URLs con la optimización regex."""
    app = create_app()
    with app.test_request_context('/', base_url='http://127.0.0.1:5000'):
        # Valid URLs
        assert is_safe_url('/dashboard') is True
        assert is_safe_url('/admin/logs?page=2&status=SUCCESS') is True
        assert is_safe_url('http://127.0.0.1:5000/perfil') is True

        # Embedded control characters rejection (\x00 - \x1f, \x7f)
        assert is_safe_url('/dash\x00board') is False
        assert is_safe_url('/dash\x07board') is False
        assert is_safe_url('/dash\x1fboard') is False
        assert is_safe_url('/dash\x7fboard') is False

        # Embedded whitespace rejection (spaces, tabs, newlines)
        assert is_safe_url('/dash board') is False
        assert is_safe_url('/dash\tboard') is False
        assert is_safe_url('/dash\nboard') is False

        # Unsafe redirect targets
        assert is_safe_url('//evil.com') is False
        assert is_safe_url('http://evil.com') is False
        assert is_safe_url('%2f%2fevil.com') is False
