from unittest.mock import patch
from app import create_app


def test_healthz_handles_unexpected_exception_gracefully():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with patch('app.routes.database_healthcheck', side_effect=RuntimeError("Unexpected connection pool crash")):
            response = client.get('/healthz')
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert data['database_ok'] is False
            assert data['app'] == 'GameVault'


def test_salud_alias_handles_unexpected_exception_gracefully():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with patch('app.routes.database_healthcheck', side_effect=Exception("Database driver failure")):
            response = client.get('/salud')
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert data['database_ok'] is False
            assert data['app'] == 'GameVault'
