"""Test local variable total_games optimization in obtener_metricas_coleccion."""

import uuid
from app import create_app
from app.models import (
    Base,
    Game,
    User,
    crear_juego,
    crear_usuario,
    get_engine,
    get_session_factory,
    obtener_metricas_coleccion,
)


def test_obtener_metricas_coleccion_local_total_games():
    """Verifica que obtener_metricas_coleccion retorne métricas correctas usando la variable local total_games."""
    app = create_app()
    with app.app_context():
        engine = get_engine()
        Base.metadata.create_all(engine)
        session_factory = get_session_factory()

        with session_factory() as session:
            session.query(Game).delete()
            session.query(User).delete()
            session.commit()

        # Test empty user
        u_empty = crear_usuario("TestEmpty", "User", f"empty_{uuid.uuid4()}@test.com", "+56", "912345678", "hash12345678")
        metrics_empty = obtener_metricas_coleccion(u_empty['user_id'], full=True)
        assert metrics_empty['total_games'] == 0
        assert metrics_empty['last_updated_game'] is None
        assert metrics_empty['next_focus'] is None

        # Test user with games
        u_games = crear_usuario("TestWithGames", "User", f"games_{uuid.uuid4()}@test.com", "+56", "912345678", "hash12345678")
        uid = u_games['user_id']
        crear_juego(
            user_id=uid,
            game_id=str(uuid.uuid4()),
            titulo="Elden Ring",
            descripcion="Action RPG",
            imagen_url="",
            plataforma="PlayStation",
            estado="Nuevo",
            categoria="Jugando",
            prioridad="Alta",
            calificacion=10,
            es_favorito=True,
        )

        metrics_populated = obtener_metricas_coleccion(uid, full=True)
        assert metrics_populated['total_games'] == 1
        assert metrics_populated['high_priority_count'] == 1
        assert metrics_populated['last_updated_game']['titulo'] == "Elden Ring"
        assert metrics_populated['next_focus']['titulo'] == "Elden Ring"
