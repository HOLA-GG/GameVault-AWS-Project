"""Pruebas de robustez para helper functions de URL y fechas frente a tipos de datos no válidos."""

from app.models import crear_url_firmada_lectura, eliminar_imagen_s3, parse_date_filter
from app.routes import is_safe_url, is_valid_presigned_image_url, parse_iso_datetime


def test_is_valid_presigned_image_url_non_string_types():
    assert is_valid_presigned_image_url(None) is False
    assert is_valid_presigned_image_url(12345) is False
    assert is_valid_presigned_image_url(['http://example.com/covers/img.jpg']) is False
    assert is_valid_presigned_image_url({'url': 'http://example.com'}) is False


def test_is_safe_url_non_string_types():
    assert is_safe_url(None) is False
    assert is_safe_url(12345) is False
    assert is_safe_url(['/dashboard']) is False
    assert is_safe_url({'redirect': '/dashboard'}) is False


def test_parse_iso_datetime_non_string_types():
    assert parse_iso_datetime(None) is None
    assert parse_iso_datetime(20250101) is None
    assert parse_iso_datetime(['2025-01-01T00:00:00Z']) is None
    assert parse_iso_datetime({'date': '2025-01-01'}) is None


def test_parse_date_filter_non_string_types():
    assert parse_date_filter(None) is None
    assert parse_date_filter(20250101) is None
    assert parse_date_filter(['2025-01-01']) is None
    assert parse_date_filter({'date': '2025-01-01'}) is None


def test_eliminar_imagen_s3_non_string_types():
    assert eliminar_imagen_s3(None) is True
    assert eliminar_imagen_s3(12345) is True
    assert eliminar_imagen_s3(['/static/uploads/covers/test.jpg']) is True
    assert eliminar_imagen_s3({'url': '/static/uploads/covers/test.jpg'}) is True


def test_crear_url_firmada_lectura_non_string_types():
    assert crear_url_firmada_lectura(None) == ''
    assert crear_url_firmada_lectura(12345) == ''
    assert crear_url_firmada_lectura(['http://example.com']) == ''
    assert crear_url_firmada_lectura({'url': 'http://example.com'}) == ''
