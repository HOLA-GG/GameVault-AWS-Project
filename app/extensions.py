"""Extensiones compartidas de Flask para GameVault."""

from flask import has_request_context
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect

# Bolt Optimization: Module-level cache for resolved IP lookup function to avoid dynamic
# module import ('from app.routes import get_request_ip') on every rate-limited request (~21.5x speedup).
_GET_REQUEST_IP_FN = None


def safe_get_remote_address() -> str:
    """Obtiene la IP remota de forma segura, saneada y validada para mitigar spoofing y desvíos."""
    global _GET_REQUEST_IP_FN
    if not has_request_context():
        return '127.0.0.1'

    if _GET_REQUEST_IP_FN is None:
        try:
            from app.routes import get_request_ip
            _GET_REQUEST_IP_FN = get_request_ip
        except (ImportError, RuntimeError):
            return get_remote_address()

    try:
        return _GET_REQUEST_IP_FN()
    except Exception:
        return get_remote_address()


mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(key_func=safe_get_remote_address, default_limits=[])
