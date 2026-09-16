"""Pruebas de seguridad e inmunidad para sanitize_and_validate_ip contra tipos no-string y DoS por longitud."""

from app.models import sanitize_and_validate_ip


def test_sanitize_and_validate_ip_non_string_types():
    assert sanitize_and_validate_ip(None) == 'unknown'
    assert sanitize_and_validate_ip(12345) == 'unknown'
    assert sanitize_and_validate_ip(0) == 'unknown'
    assert sanitize_and_validate_ip(['127.0.0.1']) == 'unknown'
    assert sanitize_and_validate_ip({'ip': '127.0.0.1'}) == 'unknown'


def test_sanitize_and_validate_ip_oversized_string():
    oversized_ip = '127.0.0.1' + 'a' * 150
    assert sanitize_and_validate_ip(oversized_ip) == 'unknown'


def test_sanitize_and_validate_ip_valid_and_normalized_ips():
    assert sanitize_and_validate_ip('192.168.1.1') == '192.168.1.1'
    assert sanitize_and_validate_ip('  10.0.0.1:8080 ') == '10.0.0.1'
    assert sanitize_and_validate_ip(' invalid.ip.addr ') == 'unknown'
