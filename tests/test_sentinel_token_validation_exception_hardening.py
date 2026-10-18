import os
import sys
import pytest

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_sentinel_token_validation.db'
    if os.path.exists(db_file):
        os.remove(db_file)

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')

    # Force reload of app and models
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
        except Exception:
            pass


def test_validar_reset_token_exception_handling(app, monkeypatch):
    """Verifies that validar_reset_token catches unexpected exceptions and returns a structured error dict."""
    import app.models

    def mock_obtener_token_por_valor(reset_token, only_active=True):
        raise Exception("Database connection lost during token lookup")

    monkeypatch.setattr(app.models, 'obtener_token_por_valor', mock_obtener_token_por_valor)

    res = app.models.validar_reset_token("some_token")
    assert res['valid'] is False
    assert res['user_id'] is None
    assert res['error'] == 'Error al validar token de recuperación'


def test_usar_token_exception_handling(app, monkeypatch):
    """Verifies that usar_token catches unexpected exceptions and returns a structured error dict."""
    import app.models

    def mock_get_session_factory():
        class MockSession:
            def __enter__(self):
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass
            def scalar(self, stmt):
                raise Exception("Database error during token usage")
        return MockSession

    monkeypatch.setattr(app.models, 'get_session_factory', mock_get_session_factory)

    res = app.models.usar_token("some_token")
    assert res['success'] is False
    assert res['error'] == 'Error al procesar el token'
