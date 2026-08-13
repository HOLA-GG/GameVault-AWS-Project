"""Extensiones compartidas de Flask para GameVault."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail
from flask_wtf.csrf import CSRFProtect


def safe_get_remote_address() -> str:
    """Obtiene la IP remota de forma segura, saneada y validada para mitigar spoofing y desvíos."""
    from flask import has_request_context
    if not has_request_context():
        return '127.0.0.1'

    # Importar dinámicamente para evitar importación circular
    try:
        from app.routes import get_request_ip
        return get_request_ip()
    except (ImportError, RuntimeError):
        return get_remote_address()


mail = Mail()
csrf = CSRFProtect()
limiter = Limiter(key_func=safe_get_remote_address, default_limits=[])
