"""Prueba unitaria para verificar la optimización y corrección de normalize_game_metadata."""

import pytest
from app.routes import normalize_game_metadata


def test_normalize_game_metadata_valid_inputs():
    form_data = {
        'plataforma': 'PlayStation',
        'estado': 'Como Nuevo',
        'categoria': 'Jugando',
        'prioridad': 'Alta',
        'calificacion': '9',
        'es_favorito': 'on',
    }
    result = normalize_game_metadata(form_data)
    assert result == {
        'plataforma': 'PlayStation',
        'estado': 'Como Nuevo',
        'categoria': 'Jugando',
        'prioridad': 'Alta',
        'calificacion': 9,
        'es_favorito': True,
    }


def test_normalize_game_metadata_invalid_inputs_fallback():
    form_data = {
        'plataforma': 'Sega Genesis',
        'estado': 'Invalido',
        'categoria': 'Desconocida',
        'prioridad': 'Ultra',
        'calificacion': '99',
        'es_favorito': 'off',
    }
    result = normalize_game_metadata(form_data)
    assert result == {
        'plataforma': 'PC',
        'estado': 'N/A',
        'categoria': 'Biblioteca',
        'prioridad': 'Media',
        'calificacion': None,
        'es_favorito': False,
    }


def test_normalize_game_metadata_empty_and_null_inputs():
    form_data = {}
    result = normalize_game_metadata(form_data)
    assert result == {
        'plataforma': 'PC',
        'estado': 'N/A',
        'categoria': 'Biblioteca',
        'prioridad': 'Media',
        'calificacion': None,
        'es_favorito': False,
    }
