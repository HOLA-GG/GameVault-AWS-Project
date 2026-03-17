#!/usr/bin/env python3
"""Arranque local de desarrollo para GameVault."""

from __future__ import annotations

import os

from app import create_app


app = create_app()


def env_bool(name: str, default: bool = False) -> bool:
    """Convierte variables comunes a booleano."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


if __name__ == '__main__':
    host = os.environ.get('FLASK_RUN_HOST', '127.0.0.1')
    port = int(os.environ.get('FLASK_RUN_PORT', '5000'))
    debug = env_bool('FLASK_DEBUG', app.config['APP_ENV'] != 'production')

    print('=' * 60)
    print('GAMEVAULT LOCAL')
    print('=' * 60)
    print(f"Entorno: {app.config['APP_ENV']}")
    print(f"Host: {host}:{port}")
    print(f"Debug: {debug}")
    print(f"Base de datos: {app.config['DATABASE_BACKEND']}")
    print(f"Storage: {app.config['STORAGE_BACKEND']}")
    print('=' * 60)

    app.run(host=host, port=port, debug=debug)
