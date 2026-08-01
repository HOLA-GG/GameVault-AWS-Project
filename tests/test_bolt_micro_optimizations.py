from __future__ import annotations

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.routes import get_action_badge_class
from app.models import _user_row_to_dict, _game_row_to_dict, _audit_log_row_to_dict, MIN_DATE, utcnow

# Mock Row with _mapping
class MockRow:
    def __init__(self, mapping_dict):
        self._mapping = mapping_dict

# Mock ORM object
class MockORM:
    def __init__(self, attr_dict):
        for k, v in attr_dict.items():
            setattr(self, k, v)


def test_get_action_badge_class_cases():
    """Verify that get_action_badge_class works correctly with different casing and returns standard fallbacks."""
    # Exact match
    assert get_action_badge_class('LOGIN') == 'action-auth'
    # Lowercase pre-populated match
    assert get_action_badge_class('login') == 'action-auth'
    # Mixed case fallback
    assert get_action_badge_class('lOgIn') == 'action-auth'
    # Unknown action
    assert get_action_badge_class('UNKNOWN_ACTION_ABC') == 'action-generic'
    # Empty/None check
    assert get_action_badge_class('') == 'action-generic'
    assert get_action_badge_class(None) == 'action-generic'


def test_row_to_dict_try_except_mapping_fallback():
    """Verify row to dict helpers map both _mapping Row objects and standard ORM objects correctly."""
    now_dt = utcnow()

    # User Row Mapping
    user_mapping = {
        'user_id': 'u1',
        'email': 'u1@test.com',
        'nombre': 'User 1',
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    user_row = MockRow(user_mapping)
    user_dict = _user_row_to_dict(user_row, format_dates=False)
    assert user_dict['user_id'] == 'u1'
    assert user_dict['email'] == 'u1@test.com'
    assert user_dict['created_at'] == now_dt

    # User ORM object
    user_orm_data = {
        'user_id': 'u2',
        'email': 'u2@test.com',
        'nombre': 'User 2',
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    user_orm = MockORM(user_orm_data)
    user_dict_orm = _user_row_to_dict(user_orm, format_dates=False)
    assert user_dict_orm['user_id'] == 'u2'
    assert user_dict_orm['email'] == 'u2@test.com'
    assert user_dict_orm['created_at'] == now_dt

    # Game Row Mapping
    game_mapping = {
        'game_id': 'g1',
        'user_id': 'u1',
        'titulo': 'Test Game',
        'descripcion': 'A game description',
        'imagen_url': 'covers/img.jpg',
        'plataforma': 'Xbox',
        'estado': 'Bueno',
        'categoria': 'Backlog',
        'prioridad': 'Media',
        'calificacion': 8,
        'es_favorito': True,
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    game_row = MockRow(game_mapping)
    game_dict = _game_row_to_dict(game_row, format_dates=False)
    assert game_dict['game_id'] == 'g1'
    assert game_dict['titulo'] == 'Test Game'
    assert game_dict['titulo_lower'] == 'test game'
    assert game_dict['plataforma_lower'] == 'xbox'
    assert game_dict['es_favorito'] is True

    # Game ORM object
    game_orm_data = {
        'game_id': 'g2',
        'user_id': 'u2',
        'titulo': 'Another Game',
        'descripcion': 'Desc',
        'imagen_url': None,
        'plataforma': 'PC',
        'estado': 'N/A',
        'categoria': 'Biblioteca',
        'prioridad': 'Media',
        'calificacion': None,
        'es_favorito': False,
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    game_orm = MockORM(game_orm_data)
    game_dict_orm = _game_row_to_dict(game_orm, format_dates=False)
    assert game_dict_orm['game_id'] == 'g2'
    assert game_dict_orm['titulo'] == 'Another Game'
    assert game_dict_orm['titulo_lower'] == 'another game'
    assert game_dict_orm['es_favorito'] is False
