"""Tests for Bolt Optimization: defaultdict(int) in build_dashboard_insights."""

from datetime import datetime, timezone
from app.routes import build_dashboard_insights


def test_build_dashboard_insights_defaultdict_aggregation():
    """Verify build_dashboard_insights calculates correct counts, filters, and dominant attributes using defaultdict."""
    now = datetime.now(timezone.utc)
    juegos = [
        {
            'game_id': 'g1',
            'plataforma': 'Nintendo Switch',
            'estado': 'Como Nuevo',
            'categoria': 'Jugando',
            'prioridad': 'Alta',
            'imagen_url': 'http://example.com/cover.jpg',
            'es_favorito': True,
            'calificacion': 10,
            'updated_at': now,
            'created_at': now,
        },
        {
            'game_id': 'g2',
            'plataforma': 'Nintendo Switch',
            'estado': 'Como Nuevo',
            'categoria': 'Completado',
            'prioridad': 'Media',
            'imagen_url': '',
            'es_favorito': False,
            'calificacion': 8,
            'updated_at': now,
            'created_at': now,
        },
        {
            'game_id': 'g3',
            'plataforma': 'PlayStation 5',
            'estado': 'Nuevo',
            'categoria': 'Backlog',
            'prioridad': 'Baja',
            'imagen_url': 'http://example.com/cover2.jpg',
            'es_favorito': True,
            'calificacion': None,
            'updated_at': now,
            'created_at': now,
        },
    ]

    insights = build_dashboard_insights(juegos)

    # Check totals and scalar counts
    assert insights['total_games'] == 3
    assert insights['platforms_count'] == 2
    assert insights['missing_images'] == 1
    assert insights['favorites_count'] == 2
    assert insights['high_priority_count'] == 1
    assert insights['backlog_count'] == 1
    assert insights['currently_playing_count'] == 1
    assert insights['average_rating'] == 9.0

    # Dominant metrics
    assert insights['dominant_platform'] == {'label': 'Nintendo Switch', 'count': 2}
    assert insights['dominant_status'] == {'label': 'Como Nuevo', 'count': 2}

    # Filter options (sorted keys from defaultdict)
    assert insights['filter_options']['plataformas'] == ['Nintendo Switch', 'PlayStation 5']
    assert insights['filter_options']['estados'] == ['Como Nuevo', 'Nuevo']
    assert insights['filter_options']['categorias'] == ['Backlog', 'Completado', 'Jugando']


def test_build_dashboard_insights_empty_collection():
    """Verify build_dashboard_insights handles empty collection without error."""
    insights = build_dashboard_insights([])

    assert insights['total_games'] == 0
    assert insights['platforms_count'] == 0
    assert insights['missing_images'] == 0
    assert insights['favorites_count'] == 0
    assert insights['average_rating'] is None
    assert insights['dominant_platform'] == {'label': 'Sin juegos', 'count': 0}
    assert insights['filter_options']['plataformas'] == []
