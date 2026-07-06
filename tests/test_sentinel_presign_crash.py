import pytest
from app import create_app
from app.models import get_session_factory, User, generate_password_hash
import json
import hashlib
import uuid
import os

@pytest.fixture
def app():
    os.environ['STORAGE_BACKEND'] = 's3'
    app = create_app()
    app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
    })
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_presign_upload_json_int_no_crash(client):
    # 1. Create user and set session
    unique_id = str(uuid.uuid4())
    pw_hash = generate_password_hash('password123')
    session_factory = get_session_factory()
    with session_factory() as db_session:
        user = User(
            user_id=unique_id,
            email=f'test-{unique_id}@example.com',
            nombre='Test User',
            password_hash=pw_hash,
            status='active',
            role='user'
        )
        db_session.add(user)
        db_session.commit()

    with client.session_transaction() as sess:
        sess['user_id'] = unique_id
        sess['_pw_hash'] = hashlib.sha256(pw_hash.encode('utf-8')).hexdigest()

    # 2. Try to send an int in JSON instead of a string
    response = client.post(
        '/api/uploads/presign',
        data=json.dumps({'filename': 123, 'content_type': 'image/jpeg'}),
        content_type='application/json'
    )

    # It SHOULD NOT fail with 500
    assert response.status_code != 500
    # Since 123 converted to '123' doesn't have an extension, it fails validation with 400
    assert response.status_code == 400
