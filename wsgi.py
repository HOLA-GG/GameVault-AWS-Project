"""Entrada WSGI para producción."""

from app import create_app


application = create_app()

