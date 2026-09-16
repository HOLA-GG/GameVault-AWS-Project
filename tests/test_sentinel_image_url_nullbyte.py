"""Pruebas de seguridad para rechazar null bytes en URLs de imágenes."""

from app.routes import is_valid_presigned_image_url
from tests.test_app import app


def test_is_valid_presigned_image_url_nullbyte_rejection(app):
    """Verifica que is_valid_presigned_image_url rechace URLs que contengan null bytes."""
    with app.app_context():
        # Raw null byte
        assert is_valid_presigned_image_url("http://example.com/covers/image.jpg\x00.php") is False
        # Percent-encoded null byte
        assert is_valid_presigned_image_url("http://example.com/covers/image.jpg%00.png") is False
