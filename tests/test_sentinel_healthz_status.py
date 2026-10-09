from unittest.mock import patch
from app import create_app


def test_healthz_returns_200_when_db_healthy():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with patch('app.routes.database_healthcheck', return_value=True):
            response = client.get('/healthz')
            assert response.status_code == 200
            data = response.get_json()
            assert data['status'] == 'ok'
            assert data['database_ok'] is True


def test_healthz_returns_503_when_db_unhealthy():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with patch('app.routes.database_healthcheck', return_value=False):
            response = client.get('/healthz')
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert data['database_ok'] is False


def test_salud_alias_reflects_db_status():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        with patch('app.routes.database_healthcheck', return_value=False):
            response = client.get('/salud')
            assert response.status_code == 503
            data = response.get_json()
            assert data['status'] == 'unhealthy'
            assert data['database_ok'] is False
