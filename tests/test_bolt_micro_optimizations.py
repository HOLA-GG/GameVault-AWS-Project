from __future__ import annotations

import sys
from pathlib import Path
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime, timezone
from app.routes import get_action_badge_class, filter_and_sort_games, enrich_game_metadata, enrich_log_metadata
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
    """Verify row to dict helpers map both full/partial _mapping Row objects and standard ORM objects correctly."""
    now_dt = utcnow()

    # Partial User Row Mapping (len < 13)
    user_partial_mapping = {
        'user_id': 'u1',
        'email': 'u1@test.com',
        'nombre': 'User 1',
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    user_partial_row = MockRow(user_partial_mapping)
    user_partial_dict = _user_row_to_dict(user_partial_row, format_dates=False)
    assert user_partial_dict['user_id'] == 'u1'
    assert user_partial_dict['email'] == 'u1@test.com'
    assert user_partial_dict['created_at'] == now_dt

    # Full User Row Mapping (len == 13)
    user_full_mapping = {
        'user_id': 'u1_full',
        'email': 'full@test.com',
        'nombre': 'User Full',
        'apellido': 'Smith',
        'prefijo_pais': '+1',
        'telefono': '5551234',
        'password_hash': 'hash123',
        'role': 'user',
        'status': 'active',
        'collection_visibility': 'public',
        'homepage_showcase_opt_in': True,
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    user_full_row = MockRow(user_full_mapping)
    user_full_dict = _user_row_to_dict(user_full_row, format_dates=False)
    assert user_full_dict['user_id'] == 'u1_full'
    assert user_full_dict['collection_visibility'] == 'public'
    assert user_full_dict['homepage_showcase_opt_in'] is True

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

    # Full Game Row Mapping (len == 13)
    game_full_mapping = {
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
    game_full_row = MockRow(game_full_mapping)
    game_dict = _game_row_to_dict(game_full_row, format_dates=False)
    assert game_dict['game_id'] == 'g1'
    assert game_dict['titulo'] == 'Test Game'
    assert game_dict['titulo_lower'] == 'test game'
    assert game_dict['plataforma_lower'] == 'xbox'
    assert game_dict['es_favorito'] is True

    # Partial Game Row Mapping (len < 13)
    game_partial_mapping = {
        'game_id': 'g_part',
        'user_id': 'u1',
        'titulo': 'Partial Game',
        'created_at': now_dt,
        'updated_at': now_dt,
    }
    game_partial_row = MockRow(game_partial_mapping)
    game_part_dict = _game_row_to_dict(game_partial_row, format_dates=False)
    assert game_part_dict['game_id'] == 'g_part'
    assert game_part_dict['titulo'] == 'Partial Game'
    assert game_part_dict['plataforma'] == 'PC'

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

    # Full AuditLog Row Mapping (len == 10)
    log_full_mapping = {
        'audit_id': 'log_full_1',
        'user_id': 'u1',
        'action': 'LOGIN',
        'action_name': 'Inicio de sesión',
        'resource': 'auth',
        'timestamp': now_dt,
        'ip_address': '127.0.0.1',
        'user_agent': 'Mozilla/5.0',
        'details': {'ip': '127.0.0.1'},
        'status': 'SUCCESS',
    }
    log_full_row = MockRow(log_full_mapping)
    log_full_dict = _audit_log_row_to_dict(log_full_row, format_dates=False)
    assert log_full_dict['audit_id'] == 'log_full_1'
    assert log_full_dict['action'] == 'LOGIN'
    assert log_full_dict['user_agent'] == 'Mozilla/5.0'

    # Partial AuditLog Row Mapping (len == 9, user_agent omitted)
    log_partial_mapping = {
        'audit_id': 'log_part_1',
        'user_id': 'u1',
        'action': 'LOGIN',
        'action_name': 'Inicio de sesión',
        'resource': 'auth',
        'timestamp': now_dt,
        'ip_address': '127.0.0.1',
        'details': {},
        'status': 'SUCCESS',
    }
    log_part_row = MockRow(log_partial_mapping)
    log_part_dict = _audit_log_row_to_dict(log_part_row, format_dates=False)
    assert log_part_dict['audit_id'] == 'log_part_1'
    assert log_part_dict['action'] == 'LOGIN'
    assert log_part_dict['user_agent'] == 'unknown'


def test_filter_and_sort_games_eafp_text_search():
    """Verify filter_and_sort_games text search works with both cached lower fields and fallback fields."""
    juegos = [
        {
            'plataforma': 'Nintendo Switch',
            'estado': 'Como Nuevo',
            'categoria': 'Biblioteca',
            'es_favorito': False,
            'titulo': 'Zelda Breath of the Wild',
            'descripcion': 'Open world adventure',
            'plataforma_lower': 'nintendo switch',
            'estado_lower': 'como nuevo',
            'titulo_lower': 'zelda breath of the wild',
            'descripcion_lower': 'open world adventure',
        },
        {
            # Legacy/minimal dict without lower fields
            'plataforma': 'PlayStation 5',
            'estado': 'Nuevo',
            'categoria': 'Jugando',
            'es_favorito': True,
            'titulo': 'Final Fantasy VII',
            'descripcion': 'Classic RPG remake',
        },
    ]

    # Search query matching first item using lowercased cache
    res1 = filter_and_sort_games(juegos, {'q': 'zelda'})
    assert len(res1) == 1
    assert res1[0]['titulo'] == 'Zelda Breath of the Wild'

    # Search query matching second item via KeyError fallback
    res2 = filter_and_sort_games(juegos, {'q': 'fantasy'})
    assert len(res2) == 1
    assert res2[0]['titulo'] == 'Final Fantasy VII'

    # Search query matching neither
    res3 = filter_and_sort_games(juegos, {'q': 'halo'})
    assert len(res3) == 0


def test_enrich_game_and_log_metadata():
    """Verify that enrich_game_metadata and enrich_log_metadata handle None, unenriched, and enriched dictionaries."""
    now_dt = datetime.now(timezone.utc)

    # None input
    assert enrich_game_metadata(None) is None
    assert enrich_log_metadata(None) is None

    # Unenriched game
    game = {
        'imagen_url': 'http://example.com/cover.jpg',
        'updated_at': now_dt,
        'created_at': now_dt,
    }
    enriched_game = enrich_game_metadata(game)
    assert enriched_game is not None
    assert enriched_game['_enriched'] is True
    assert isinstance(enriched_game['updated_at'], str)
    assert isinstance(enriched_game['created_at'], str)

    # Already enriched game (should short-circuit and return immediately)
    already_enriched_game = {'_enriched': True, 'imagen_url': 'already'}
    res_game = enrich_game_metadata(already_enriched_game)
    assert res_game is already_enriched_game
    assert res_game['imagen_url'] == 'already'

    # Unenriched log
    log = {
        'action': 'LOGIN',
        'status': 'SUCCESS',
        'timestamp': now_dt,
    }
    enriched_log = enrich_log_metadata(log)
    assert enriched_log is not None
    assert enriched_log['_enriched'] is True
    assert enriched_log['action_badge_class'] == 'action-auth'
    assert enriched_log['status_badge_class'] == 'badge-log-success'
    assert isinstance(enriched_log['timestamp'], str)

    # Already enriched log (should short-circuit and return immediately)
    already_enriched_log = {'_enriched': True, 'action': 'LOGIN'}
    res_log = enrich_log_metadata(already_enriched_log)
    assert res_log is already_enriched_log
