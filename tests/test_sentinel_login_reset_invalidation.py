import pytest
import uuid
import sys
import os
from sqlalchemy import select

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_login_invalidation.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models to ensure test db is correctly loaded
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
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

def test_login_invalidates_outstanding_reset_tokens(client, app):
    """Verifies that outstanding reset tokens for a user are deleted upon successful login,
    while other users' reset tokens are preserved."""
    from app.models import get_session_factory, User, PasswordResetToken, crear_usuario, crear_reset_token

    # 1. Create two users: User A and User B
    email_a = "usera@example.com"
    email_b = "userb@example.com"
    pass_a = "SecurePass123!"
    pass_b = "SecurePass123!"

    user_a = crear_usuario("User A", "Test", email_a, "", "", "hash")
    user_b = crear_usuario("User B", "Test", email_b, "", "", "hash")

    # Override the hash in database to be a valid scrypt/werkzeug hash so check_password_hash succeeds
    from werkzeug.security import generate_password_hash
    session_factory = get_session_factory()
    with session_factory() as session:
        db_user_a = session.scalar(select(User).where(User.user_id == user_a['user_id']))
        db_user_a.password_hash = generate_password_hash(pass_a)

        db_user_b = session.scalar(select(User).where(User.user_id == user_b['user_id']))
        db_user_b.password_hash = generate_password_hash(pass_b)
        session.commit()

    # 2. Create active reset tokens for both users
    token_a_res = crear_reset_token(user_a['user_id'], "127.0.0.1")
    token_b_res = crear_reset_token(user_b['user_id'], "127.0.0.1")

    assert token_a_res['success'] is True
    assert token_b_res['success'] is True

    # 3. Verify tokens exist in the database before login
    with session_factory() as session:
        tokens_a = session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user_a['user_id'])).all()
        tokens_b = session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user_b['user_id'])).all()
        assert len(tokens_a) == 1
        assert len(tokens_b) == 1

    # 4. Perform successful login for User A
    response = client.post('/login', data={
        'email': email_a,
        'password': pass_a
    })
    assert response.status_code == 302

    # 5. Verify that User A's outstanding reset tokens have been deleted from the database
    with session_factory() as session:
        tokens_a_after = session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user_a['user_id'])).all()
        tokens_b_after = session.scalars(select(PasswordResetToken).where(PasswordResetToken.user_id == user_b['user_id'])).all()

        # User A's token should be completely deleted
        assert len(tokens_a_after) == 0
        # User B's token should be completely preserved
        assert len(tokens_b_after) == 1
