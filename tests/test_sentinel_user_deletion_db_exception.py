from unittest.mock import patch

def test_eliminar_usuario_db_exception():
    import app.models
    with patch('app.models.get_session_factory', side_effect=Exception('DB connection failed')):
        result = app.models.eliminar_usuario('valid-user-id-12345')
        assert result == {'success': False, 'error': 'Error al eliminar usuario'}
