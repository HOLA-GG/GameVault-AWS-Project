import unittest
from unittest.mock import patch, MagicMock
import hashlib
from app import create_app


class GameAuditTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.app.config['STORAGE_BACKEND'] = 's3'
        self.client = self.app.test_client()

    @patch('app.routes.obtener_usuario_por_id')
    @patch('app.routes.crear_log_audit')
    @patch('app.routes.subir_imagen_a_s3')
    def test_agregar_juego_image_upload_failed_audit(self, mock_subir, mock_log_audit, mock_get_user):
        pwd_hash = 'scrypt:32768:8:1$dummy$dummy'
        mock_get_user.return_value = {
            'user_id': 'user-123',
            'status': 'active',
            'role': 'user',
            'password_hash': pwd_hash,
        }
        mock_subir.return_value = None  # Upload fails

        pw_hash_gen = hashlib.sha256(pwd_hash.encode('utf-8')).hexdigest()

        headers = {'User-Agent': 'TestAgent/1.0'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'user-123'
                sess['_pw_hash'] = pw_hash_gen
                sess['_user_agent'] = 'TestAgent/1.0'

            with patch('app.routes.is_valid_image_file', return_value=(True, None)):
                # Provide a FileStorage mock object where filename is truthy
                file_mock = MagicMock()
                file_mock.filename = 'test.jpg'

                data = {
                    'titulo': 'Test Game',
                    'descripcion': 'Test Description',
                    'plataforma': 'PC',
                    'estado': 'Nuevo',
                    'imagen': file_mock,
                }
                res = c.post('/agregar', data=data, headers=headers, content_type='multipart/form-data', follow_redirects=True)
                self.assertEqual(res.status_code, 200)

                failed_logs = [kwargs for args, kwargs in mock_log_audit.call_args_list if kwargs.get('status') == 'FAILED' and kwargs.get('details', {}).get('reason') == 'image_upload_failed']
                self.assertEqual(len(failed_logs), 1)

    @patch('app.routes.obtener_usuario_por_id')
    @patch('app.routes.crear_log_audit')
    @patch('app.routes.crear_juego')
    def test_agregar_juego_db_save_failed_audit(self, mock_crear_juego, mock_log_audit, mock_get_user):
        pwd_hash = 'scrypt:32768:8:1$dummy$dummy'
        mock_get_user.return_value = {
            'user_id': 'user-123',
            'status': 'active',
            'role': 'user',
            'password_hash': pwd_hash,
        }
        mock_crear_juego.return_value = None  # DB save fails

        pw_hash_gen = hashlib.sha256(pwd_hash.encode('utf-8')).hexdigest()

        headers = {'User-Agent': 'TestAgent/1.0'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'user-123'
                sess['_pw_hash'] = pw_hash_gen
                sess['_user_agent'] = 'TestAgent/1.0'

            data = {
                'titulo': 'Test Game',
                'descripcion': 'Test Description',
                'plataforma': 'PC',
                'estado': 'Nuevo',
            }
            res = c.post('/agregar', data=data, headers=headers, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            failed_logs = [kwargs for args, kwargs in mock_log_audit.call_args_list if kwargs.get('status') == 'FAILED' and kwargs.get('details', {}).get('reason') == 'db_save_failed']
            self.assertEqual(len(failed_logs), 1)

    @patch('app.routes.obtener_usuario_por_id')
    @patch('app.routes.obtener_juego_por_id')
    @patch('app.routes.actualizar_juego')
    @patch('app.routes.crear_log_audit')
    def test_editar_juego_db_update_failed_audit(self, mock_log_audit, mock_actualizar_juego, mock_get_game, mock_get_user):
        pwd_hash = 'scrypt:32768:8:1$dummy$dummy'
        mock_get_user.return_value = {
            'user_id': 'user-123',
            'status': 'active',
            'role': 'user',
            'password_hash': pwd_hash,
        }
        mock_get_game.return_value = {'id': 'game-123', 'titulo': 'Old Title', 'descripcion': 'Old Desc', 'imagen_url': '', 'updated_at': None, 'created_at': None}
        mock_actualizar_juego.return_value = {'success': False, 'error': 'Database lock error'}

        pw_hash_gen = hashlib.sha256(pwd_hash.encode('utf-8')).hexdigest()

        headers = {'User-Agent': 'TestAgent/1.0'}
        with self.client as c:
            with c.session_transaction() as sess:
                sess['user_id'] = 'user-123'
                sess['_pw_hash'] = pw_hash_gen
                sess['_user_agent'] = 'TestAgent/1.0'

            data = {
                'titulo': 'Updated Game',
                'descripcion': 'Updated Description',
                'plataforma': 'PC',
                'estado': 'Nuevo',
            }
            res = c.post('/edit/game-123', data=data, headers=headers, follow_redirects=True)
            self.assertEqual(res.status_code, 200)

            failed_logs = [kwargs for args, kwargs in mock_log_audit.call_args_list if kwargs.get('status') == 'FAILED' and kwargs.get('details', {}).get('reason') == 'db_update_failed']
            self.assertEqual(len(failed_logs), 1)
