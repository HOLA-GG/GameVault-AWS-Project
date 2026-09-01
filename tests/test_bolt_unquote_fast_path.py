"""
tests/test_bolt_unquote_fast_path.py

Pruebas unitarias para verificar la correcta optimización fast-path de decodificación
de URLs en is_safe_url, is_valid_presigned_image_url y obtener_key_desde_url.
"""

from app import create_app
from app.models import obtener_key_desde_url
from app.routes import is_valid_presigned_image_url, is_safe_url


def test_is_safe_url_fast_path_and_nested_decoding():
    """Verifica que is_safe_url valide URLs normales (sin %) y decodifique URLs anidadas (%252f)."""
    app = create_app()
    with app.test_request_context('/', base_url='http://127.0.0.1:5000'):
        # Standard unencoded URLs (fast path short-circuit)
        assert is_safe_url('/dashboard') is True
        assert is_safe_url('/admin/logs?page=1') is True
        assert is_safe_url('http://127.0.0.1:5000/perfil') is True

        # Malicious cross-domain or protocol relative targets
        assert is_safe_url('//evil.com') is False
        assert is_safe_url('http://evil.com') is False

        # Single and double URL-encoded targets
        assert is_safe_url('%2f%2fdashboard') is False
        assert is_safe_url('%252f%252fdashboard') is False


def test_obtener_key_desde_url_fast_path_and_encoding():
    """Verifica que obtener_key_desde_url extraiga correctamente keys con y sin caracteres codificados."""
    # Standard unencoded key (fast path short-circuit)
    key = obtener_key_desde_url('https://mybucket.s3.amazonaws.com/covers/super-mario.png')
    assert key == 'covers/super-mario.png'

    # Key with non-covers prefix should return None
    assert obtener_key_desde_url('https://mybucket.s3.amazonaws.com/private/secret.png') is None

    # Percent-encoded key
    encoded_key = obtener_key_desde_url('https://mybucket.s3.amazonaws.com/covers/mario%20bros.png')
    assert encoded_key == 'covers/mario bros.png'


def test_is_valid_presigned_image_url_fast_path():
    """Verifica is_valid_presigned_image_url con fast-path para backend local."""
    app = create_app()
    app.config['STORAGE_BACKEND'] = 'local'
    app.config['LOCAL_UPLOAD_URL_PATH'] = '/static/uploads'

    with app.test_request_context():
        # Unencoded valid local upload URL
        assert is_valid_presigned_image_url('/static/uploads/covers/test.jpg') is True

        # Invalid/outside path
        assert is_valid_presigned_image_url('/static/uploads/../secret.txt') is False

        # Percent-encoded null byte rejection
        assert is_valid_presigned_image_url('/static/uploads/covers/test%00.jpg') is False
