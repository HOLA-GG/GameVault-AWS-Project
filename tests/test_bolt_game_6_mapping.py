"""
tests/test_bolt_game_6_mapping.py - Unit test for 6-column game projection fast-path mapping.
"""

from app.models import _game_row_to_dict, MIN_DATE, _MIN_DATE_ISO


class DummyRowFull:
    def __init__(self, data):
        self._mapping = data


class DummyRow6:
    def __init__(self, data):
        self._mapping = data


def test_game_row_to_dict_6_column_mapping():
    # 13-column full row data
    full_data = {
        'game_id': 'g123',
        'user_id': 'u456',
        'titulo': 'Zelda',
        'descripcion': 'Adventure game',
        'imagen_url': 'http://example.com/cover.png',
        'plataforma': 'Switch',
        'estado': 'Completado',
        'categoria': 'Biblioteca',
        'prioridad': 'Alta',
        'calificacion': 10,
        'es_favorito': True,
        'created_at': None,
        'updated_at': None,
    }

    # 6-column selective projection data
    partial_data_6 = {
        'game_id': 'g123',
        'user_id': 'u456',
        'titulo': 'Zelda',
        'plataforma': 'Switch',
        'estado': 'Completado',
        'categoria': 'Biblioteca',
    }

    row_full = DummyRowFull(full_data)
    row_6 = DummyRow6(partial_data_6)

    dict_full = _game_row_to_dict(row_full, format_dates=True)
    dict_6 = _game_row_to_dict(row_6, format_dates=True)

    # Ensure key structures match
    assert set(dict_full.keys()) == set(dict_6.keys())

    # Verify specific fields in 6-column mapping
    assert dict_6['game_id'] == 'g123'
    assert dict_6['user_id'] == 'u456'
    assert dict_6['titulo'] == 'Zelda'
    assert dict_6['titulo_lower'] == 'zelda'
    assert dict_6['plataforma'] == 'Switch'
    assert dict_6['plataforma_lower'] == 'switch'
    assert dict_6['estado'] == 'Completado'
    assert dict_6['estado_lower'] == 'completado'
    assert dict_6['categoria'] == 'Biblioteca'
    assert dict_6['prioridad'] == 'Media'
    assert dict_6['calificacion'] is None
    assert dict_6['es_favorito'] is False
    assert dict_6['created_at'] == _MIN_DATE_ISO
    assert dict_6['updated_at'] == _MIN_DATE_ISO


def test_game_row_to_dict_6_column_mapping_no_format_dates():
    partial_data_6 = {
        'game_id': 'g999',
        'user_id': 'u888',
        'titulo': 'Mario',
        'plataforma': 'NES',
        'estado': 'N/A',
        'categoria': None,
    }

    row_6 = DummyRow6(partial_data_6)
    dict_6 = _game_row_to_dict(row_6, format_dates=False)

    assert dict_6['game_id'] == 'g999'
    assert dict_6['user_id'] == 'u888'
    assert dict_6['titulo'] == 'Mario'
    assert dict_6['categoria'] == 'Biblioteca'
    assert dict_6['created_at'] == MIN_DATE
    assert dict_6['updated_at'] == MIN_DATE
