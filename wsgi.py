"""Entrada WSGI para producción."""

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app


application = create_app()

