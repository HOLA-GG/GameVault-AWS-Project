"""Test positional tuple indexing optimization in obtener_metricas_coleccion."""

from app import create_app
from app.models import Base, Game, User, crear_juego, crear_usuario, get_engine, get_session_factory, obtener_metricas_coleccion


def test_obtener_metricas_coleccion_positional_tuple_indexing():
    """Verifica que obtener_metricas_coleccion extraiga métricas agregadas correctamente usando indexación posicional."""
    app = create_app()
    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        session_factory = get_session_factory()

        with session_factory() as session:
            session.query(Game).delete()
            session.query(User).delete()
            session.commit()

        # Create user
        user = crear_usuario('Test', 'User', 'positional_test@example.com', '+1', '12345678', 'hash12345678')
        assert user is not None
        user_id = user['user_id']

        # Empty user collection test (full=False)
        metrics_empty_fast = obtener_metricas_coleccion(user_id, full=False)
        assert metrics_empty_fast['total_games'] == 0
        assert metrics_empty_fast['missing_images'] == 0
        assert metrics_empty_fast['favorites_count'] == 0
        assert metrics_empty_fast['high_priority_count'] == 0
        assert metrics_empty_fast['average_rating'] is None

        # Empty user collection test (full=True)
        metrics_empty_full = obtener_metricas_coleccion(user_id, full=True)
        assert metrics_empty_full['total_games'] == 0
        assert metrics_empty_full['dominant_platform']['label'] == 'Sin juegos'

        # Add games with varied attributes
        g1 = crear_juego(
            user_id=user_id,
            game_id='game-pos-1',
            titulo='Zelda Tears of the Kingdom',
            descripcion='RPG de acción',
            imagen_url='',  # missing image
            plataforma='Nintendo',
            estado='Completado',
            categoria='Biblioteca',
            prioridad='Alta',
            calificacion=10,
            es_favorito=True
        )
        g2 = crear_juego(
            user_id=user_id,
            game_id='game-pos-2',
            titulo='Elden Ring',
            descripcion='Soulslike',
            imagen_url='https://example.com/elden.jpg',
            plataforma='PC',
            estado='Jugando',
            categoria='Jugando',
            prioridad='Media',
            calificacion=8,
            es_favorito=False
        )
        g3 = crear_juego(
            user_id=user_id,
            game_id='game-pos-3',
            titulo='Hollow Knight Silksong',
            descripcion='Metroidvania',
            imagen_url='',  # missing image
            plataforma='PC',
            estado='Pendiente',
            categoria='Wishlist',
            prioridad='Alta',
            calificacion=None,
            es_favorito=True
        )
        assert g1 is not None and g2 is not None and g3 is not None

        # Verify metrics with positional tuple indexing extraction
        m_fast = obtener_metricas_coleccion(user_id, full=False)
        assert m_fast['total_games'] == 3
        assert m_fast['missing_images'] == 2
        assert m_fast['favorites_count'] == 2
        assert m_fast['high_priority_count'] == 2
        assert m_fast['wishlist_count'] == 1
        assert m_fast['currently_playing_count'] == 1
        assert m_fast['average_rating'] == 9.0  # (10 + 8) / 2
        assert m_fast['platforms_count'] == 2  # Nintendo, PC

        # Verify full metrics
        m_full = obtener_metricas_coleccion(user_id, full=True)
        assert m_full['total_games'] == 3
        assert m_full['dominant_platform']['label'] == 'PC'
        assert m_full['dominant_platform']['count'] == 2
