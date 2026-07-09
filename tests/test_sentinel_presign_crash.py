import pytest
import sys
import os
import json
import hashlib
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = f'gamevault_test_presign_{uuid.uuid4().hex}.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('STORAGE_BACKEND', 's3')
    monkeypatch.setenv('BOOTSTRAP_ADMIN_ENABLED', '0')

    # Force reload of modules to ensure new DATABASE_URL is picked up
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

@pytest.fixture
def client(app):
    return app.test_client()

def test_presign_upload_json_int_no_crash(client, app):
    # 1. Create user directly in DB
    from app.models import User, get_session_factory, generate_password_hash

    pw_hash = generate_password_hash('SecurePass123!')
    user_id = str(uuid.uuid4())
    with app.app_context():
        session_factory = get_session_factory()
        with session_factory() as db_session:
            user = User(
                user_id=user_id,
                email=f'test-{user_id}@example.com',
                nombre='Test User',
                password_hash=pw_hash,
                status='active',
                role='user'
            )
            db_session.add(user)
            db_session.commit()

    # 2. Set session manually
    with client.session_transaction() as sess:
        sess['user_id'] = user_id
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 3. Try to send an int in JSON instead of a string
    response = client.post(
        '/api/uploads/presign',
        data=json.dumps({'filename': 123, 'content_type': 'image/jpeg'}),
        content_type='application/json'
    )

    # It SHOULD NOT fail with 500 (AttributeError)
    assert response.status_code != 500
    # Since 123 converted to '123' doesn't have an extension, it fails validation with 400
    assert response.status_code == 400
