import pytest
import uuid
from app.models import registrar_rating_showcase, ShowcaseRating, get_session_factory
from sqlalchemy import select
import sys
from pathlib import Path
import importlib

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    import os
    db_path = PROJECT_ROOT / 'gamevault_test_rating.db'
    if db_path.exists():
        db_path.unlink()

    env = {
        'APP_ENV': 'testing',
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL': 'sqlite+pysqlite:///:memory:',
        'STORAGE_BACKEND': 'local',
        'MAIL_SUPPRESS_SEND': 'true',
        'WTF_CSRF_ENABLED': 'false',
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    import app.models
    app.models._database_initialized = False
    app.models._engine = None
    app.models._session_factory = None
    app.models.DATABASE_URL = env['DATABASE_URL']

    app_module = importlib.import_module('app')
    flask_app = app_module.create_app()
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_rating_unique_constraint_enforcement(app):
    """
    Verifica que la restricción única en la base de datos previene
    votos duplicados desde la misma IP para la misma colección,
    incluso si se intentara bypassear la lógica de verificación manual.
    """
    subject_type = "sample"
    subject_id = f"test-unique-col-{uuid.uuid4()}"
    ip_address = "1.2.3.4"
    rating = 5

    with app.app_context():
        # 1. Registrar un voto válido
        res1 = registrar_rating_showcase(subject_type, subject_id, rating, ip_address)
        assert res1['success'] is True
        assert res1['duplicate'] is False

        # 2. Intentar registrar el mismo voto de nuevo
        # Esto debería ser atrapado por la verificación manual y devolver duplicate=True
        res2 = registrar_rating_showcase(subject_type, subject_id, rating, ip_address)
        assert res2['success'] is False
        assert res2['duplicate'] is True

        # 3. Forzar una inserción directa para probar la restricción de integridad de la DB
        # Simulamos una condición de carrera donde el manual check no ve el registro aún
        from sqlalchemy.exc import IntegrityError
        from app.models import utcnow

        session_factory = get_session_factory()
        with session_factory() as session:
            duplicate_entry = ShowcaseRating(
                rating_id=str(uuid.uuid4()),
                subject_type=subject_type,
                subject_id=subject_id,
                ip_address=ip_address,
                rating=rating,
                created_at=utcnow()
            )
            session.add(duplicate_entry)
            with pytest.raises(IntegrityError):
                session.commit()
            session.rollback()

def test_presign_upload_malformed_json(client, app):
    """
    Verifica que el endpoint de presign_upload no crashee con JSON malformado.
    """
    from app.models import get_session_factory, User
    from werkzeug.security import generate_password_hash
    import hashlib

    user_id = 'test-user-id'
    email = 'test@example.com'
    pw_hash = generate_password_hash('SecurePass123!')

    with app.app_context():
        session_factory = get_session_factory()
        with session_factory() as db_session:
            user = User(
                user_id=user_id,
                email=email,
                nombre='Test User',
                password_hash=pw_hash,
                role='user',
                status='active'
            )
            db_session.add(user)
            db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['email'] = email
        sess['nombre'] = 'Test User'
        sess['role'] = 'user'
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # Enviamos una lista en lugar de un objeto JSON
    response = client.post('/api/uploads/presign',
                          data='[1, 2, 3]',
                          content_type='application/json')

    # No debería dar 500 (Internal Server Error / AttributeError)
    assert response.status_code == 400
    assert b'filename y content_type son obligatorios' in response.data
