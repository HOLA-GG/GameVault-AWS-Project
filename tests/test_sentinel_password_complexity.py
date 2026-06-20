import pytest
from app.models import validar_password

def test_validar_password_complexity():
    # Test length requirements (already existing)
    assert not validar_password("Short1")
    assert not validar_password("a" * 129 + "1")

    # Test complexity requirements (new)
    assert not validar_password("allletters")
    assert not validar_password("12345678")
    assert not validar_password("!@#$%^&*")

    # Test valid passwords
    assert validar_password("Valid123")
    assert validar_password("Password1")
    assert validar_password("1Password")
    assert validar_password("a1b2c3d4")
