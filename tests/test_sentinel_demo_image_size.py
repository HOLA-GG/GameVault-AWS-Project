import io
import os
from werkzeug.datastructures import FileStorage
from app import create_app
from app.routes import procesar_imagen_base64


def test_procesar_imagen_base64_valid_size():
    """Verifica que procesar_imagen_base64 convierte imágenes dentro del límite a base64."""
    app = create_app()
    app.config['MAX_IMAGE_UPLOAD_BYTES'] = 1000

    with app.test_request_context():
        # Imagen de 500 bytes (dentro del límite de 1000 bytes)
        file_bytes = b'A' * 500
        storage = FileStorage(
            stream=io.BytesIO(file_bytes),
            filename='test.jpg',
            content_type='image/jpeg',
        )

        res = procesar_imagen_base64(storage)
        assert res is not None
        assert res.startswith('data:image/jpeg;base64,')


def test_procesar_imagen_base64_exceeds_size():
    """Verifica que procesar_imagen_base64 rechaza imágenes que superan el límite de tamaño para evitar DoS por memoria."""
    app = create_app()
    app.config['MAX_IMAGE_UPLOAD_BYTES'] = 1000

    with app.test_request_context():
        # Imagen de 1500 bytes (supera el límite de 1000 bytes)
        file_bytes = b'B' * 1500
        storage = FileStorage(
            stream=io.BytesIO(file_bytes),
            filename='oversized.jpg',
            content_type='image/jpeg',
        )

        res = procesar_imagen_base64(storage)
        assert res is None
