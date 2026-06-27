import pytest
from app.models import redact_sensitive_details, registrar_rating_showcase, ShowcaseRating, get_session_factory, ensure_tables
from sqlalchemy import select
import importlib
import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def app(monkeypatch):
    db_path = PROJECT_ROOT / 'gamevault_test_july.db'
    if db_path.exists():
        db_path.unlink()

    env = {
        'APP_ENV': 'testing',
        'SECRET_KEY': 'test-secret-key',
        'DATABASE_URL': 'sqlite+pysqlite:///gamevault_test_july.db',
        'STORAGE_BACKEND': 'none',
        'WTF_CSRF_ENABLED': 'false',
    }
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    for module_name in list(sys.modules):
        if module_name == 'app' or module_name.startswith('app.'):
            sys.modules.pop(module_name)

    app_module = importlib.import_module('app')
    flask_app = app_module.create_app()
    return flask_app

@pytest.fixture
def client(app):
    return app.test_client()

def test_redact_sensitive_details_new_keywords():
    """Verifica que las nuevas palabras clave sensibles sean redactadas."""
    sensitive_data = {
        "user_id": "123",
        "salt": "secret-salt",
        "otp": "123456",
        "mfa_token": "mfa-secret",
        "2fa_key": "2fa-secret",
        "certificate_data": "cert-data",
        "nonce": "nonce-value",
        "nested": {
            "otp_code": "654321"
        },
        "list": [
            {"nonce_id": "999"},
            "plain-value"
        ]
    }

    redacted = redact_sensitive_details(sensitive_data)

    assert redacted["user_id"] == "123"
    assert redacted["salt"] == "[REDACTED]"
    assert redacted["otp"] == "[REDACTED]"
    assert redacted["mfa_token"] == "[REDACTED]"
    assert redacted["2fa_key"] == "[REDACTED]"
    assert redacted["certificate_data"] == "[REDACTED]"
    assert redacted["nonce"] == "[REDACTED]"
    assert redacted["nested"]["otp_code"] == "[REDACTED]"
    assert redacted["list"][0]["nonce_id"] == "[REDACTED]"
    assert redacted["list"][1] == "plain-value"

def test_registrar_rating_showcase_ip_truncation(app):
    """Verifica que las IPs largas se trunquen sin causar errores de base de datos."""
    ensure_tables()
    # Una IP absurdamente larga (ej. malformada o IPv6 con relleno)
    long_ip = "2001:0db8:85a3:0000:0000:8a2e:0370:7334" * 10
    assert len(long_ip) > 64

    subject_id = str(uuid.uuid4())

    with app.app_context():
        result = registrar_rating_showcase("sample", subject_id, 5, long_ip)
        assert result["success"] is True

        session_factory = get_session_factory()
        with session_factory() as session:
            rating = session.scalar(
                select(ShowcaseRating).where(ShowcaseRating.subject_id == subject_id)
            )
            assert rating is not None
            assert len(rating.ip_address) <= 64
            assert rating.ip_address == long_ip[:64]

def test_permissions_policy_header(client):
    """Verifica que el header Permissions-Policy contenga las nuevas restricciones."""
    response = client.get('/')
    policy = response.headers.get('Permissions-Policy')
    assert policy is not None
    assert 'usb=()' in policy
    assert 'bluetooth=()' in policy
    assert 'hid=()' in policy
    assert 'serial=()' in policy
    assert 'camera=()' in policy
