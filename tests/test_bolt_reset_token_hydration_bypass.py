"""
tests/test_bolt_reset_token_hydration_bypass.py

Verifica la optimización Bolt para el bypass de hidratación ORM en búsquedas
de tokens de recuperación de contraseña (_reset_token_row_to_dict, obtener_token_por_valor,
obtener_token_por_user_id).
"""

import uuid
from datetime import datetime, timezone
from app import create_app
from app.models import (
    PasswordResetToken,
    _reset_token_row_to_dict,
    crear_reset_token,
    crear_usuario,
    obtener_token_por_user_id,
    obtener_token_por_valor,
    reset_token_to_dict,
)


def test_reset_token_row_to_dict_mapping_fast_path():
    """Verifica que _reset_token_row_to_dict mapea correctamente filas con _mapping view."""
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    class MockRow:
        def __init__(self, data):
            self._mapping = data

    full_row_data = {
        'token_id': 'tok-123',
        'user_id': 'usr-456',
        'reset_token': 'hashed-token-val',
        'created_at': now,
        'expires_at': now,
        'used': False,
        'used_at': None,
        'ip_address': '192.168.1.1',
    }

    mock_row = MockRow(full_row_data)
    mapped = _reset_token_row_to_dict(mock_row)

    assert mapped['token_id'] == 'tok-123'
    assert mapped['user_id'] == 'usr-456'
    assert mapped['reset_token'] == 'hashed-token-val'
    assert mapped['created_at'] == now.isoformat()
    assert mapped['expires_at'] == now.isoformat()
    assert mapped['expires_at_unix'] == int(now.timestamp())
    assert mapped['used'] is False
    assert mapped['used_at'] is None
    assert mapped['ip_address'] == '192.168.1.1'


def test_reset_token_row_to_dict_orm_fallback():
    """Verifica que _reset_token_row_to_dict y reset_token_to_dict funcionan en objetos ORM sin _mapping."""
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    token_orm = PasswordResetToken(
        token_id='tok-orm-123',
        user_id='usr-orm-456',
        reset_token='hash-orm',
        created_at=now,
        expires_at=now,
        used=True,
        used_at=now,
        ip_address='10.0.0.1',
    )

    res = reset_token_to_dict(token_orm)
    assert res['token_id'] == 'tok-orm-123'
    assert res['user_id'] == 'usr-orm-456'
    assert res['used'] is True
    assert res['used_at'] == now.isoformat()
    assert res['ip_address'] == '10.0.0.1'

    assert reset_token_to_dict(None) is None


def test_obtener_token_por_valor_y_user_id_bypass_hydration():
    """Verifica que obtener_token_por_valor y obtener_token_por_user_id obtienen datos de la DB sin hidratación ORM."""
    app = create_app()
    with app.app_context():
        email = f"bolttoken_{uuid.uuid4().hex[:8]}@example.com"
        user = crear_usuario(
            nombre='BoltToken',
            apellido='Tester',
            email=email,
            prefijo_pais='+1',
            telefono='5559876543',
            password_hash='hash12345',
        )
        assert user is not None
        user_id = user['user_id']

        created = crear_reset_token(user_id, '127.0.0.1')
        assert created['success'] is True
        raw_token = created['token']

        # Test obtener_token_por_valor
        tokens = obtener_token_por_valor(raw_token, only_active=True)
        assert len(tokens) == 1
        t = tokens[0]
        assert t['user_id'] == user_id
        assert t['used'] is False
        assert t['used_at'] is None
        assert t['ip_address'] == '127.0.0.1'

        # Test obtener_token_por_user_id
        token_by_uid = obtener_token_por_user_id(user_id)
        assert token_by_uid is not None
        assert token_by_uid['user_id'] == user_id
        assert token_by_uid['token_id'] == t['token_id']
        assert token_by_uid['used_at'] is None

        # Test invalid inputs
        assert obtener_token_por_valor('') == []
        assert obtener_token_por_valor(None) == []
        assert obtener_token_por_user_id('') is None
        assert obtener_token_por_user_id(None) is None
        assert obtener_token_por_user_id('a' * 100) is None
