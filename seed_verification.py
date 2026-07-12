import os
import uuid
from werkzeug.security import generate_password_hash
from app import create_app
from app.models import User, Game, get_session_factory, ensure_tables

os.environ['DATABASE_URL'] = 'sqlite:///verification.db'
app = create_app()
with app.app_context():
    ensure_tables()
    Session = get_session_factory()
    with Session() as session:
        # Create test user
        user = session.query(User).filter_by(email='palette@test.com').first()
        if not user:
            user = User(
                user_id=str(uuid.uuid4()),
                nombre='Palette',
                apellido='UX',
                email='palette@test.com',
                password_hash=generate_password_hash('Password123'),
                role='user',
                status='active'
            )
            session.add(user)
            session.commit()
            print(f"User created: {user.user_id}")

        user_id = user.user_id

        # Clear existing games for this user to avoid clutter
        session.query(Game).filter_by(user_id=user_id).delete()

        # Create a favorite game
        game1 = Game(
            game_id=str(uuid.uuid4()),
            user_id=user_id,
            titulo='Chrono Trigger',
            descripcion='Classic JRPG',
            plataforma='SNES',
            estado='Bueno',
            categoria='Biblioteca',
            prioridad='Alta',
            es_favorito=True
        )
        session.add(game1)

        # Create a regular game
        game2 = Game(
            game_id=str(uuid.uuid4()),
            user_id=user_id,
            titulo='Super Metroid',
            descripcion='Metroidvania peak',
            plataforma='SNES',
            estado='Bueno',
            categoria='Biblioteca',
            prioridad='Media',
            es_favorito=False
        )
        session.add(game2)

        session.commit()
        print("Test games created.")
