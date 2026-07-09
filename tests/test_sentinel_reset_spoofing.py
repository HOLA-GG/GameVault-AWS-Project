import pytest
import sys
import os
from pathlib import Path
from flask import url_for

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_spoof.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('SHOW_RESET_DEBUG_TOKEN', '1')

    # Force reload modules
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

def test_reset_password_email_spoofing(client, app):
    """Verifies that spoofing the email parameter in reset-password URL doesn't work."""
    email_real = 'real_user@example.com'
    email_spoof = 'spoofed_admin@example.com'

    # 1. Register a real user
    client.post('/registro', data={
        'nombre': 'Real User',
        'email': email_real,
        'password': 'SecurePass123!',
        'confirm_password': 'SecurePass123!'
    })

    # Logout because registro logs you in automatically
    client.post('/logout')

    # 2. Request password reset
    client.post('/forgot-password', data={'email': email_real})

    # 3. Get the token from DB (since we are in testing)
    from app.models import get_session_factory, User, PasswordResetToken
    from sqlalchemy import select

    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == email_real))
        token_record = session.scalar(
            select(PasswordResetToken)
            .where(PasswordResetToken.user_id == user.user_id)
            .order_by(PasswordResetToken.created_at.desc())
        )
        # In the app, the raw token is returned to the user, but we hash it in DB.
        # However, for simplicity in this test, let's look at how forgot_password returns it.
        # In forgot_password, it renders the template with debug_reset.
        # Let's just use a more direct approach by mocking or just re-requesting.
        pass

    # Re-request to get the debug token from response
    resp = client.post('/forgot-password', data={'email': email_real}, follow_redirects=True)
    resp_text = resp.get_data(as_text=True)

    import re
    # Match the token from the debug link
    token_match = re.search(r'/reset-password/([a-zA-Z0-9_-]+)', resp_text)
    assert token_match, "Token not found in debug response"
    token = token_match.group(1)

    # 4. Access reset password page with SPOOFED email parameter
    # URL: /reset-password/<token>?email=spoofed_admin@example.com
    reset_url = f'/reset-password/{token}?email={email_spoof}'
    resp = client.get(reset_url)
    resp_text = resp.get_data(as_text=True)

    # 5. Verify that the REAL email is displayed, NOT the spoofed one
    assert email_real in resp_text
    assert email_spoof not in resp_text
