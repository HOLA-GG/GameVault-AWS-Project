import pytest
from app.models import validar_password

def test_validar_password_complexity():
    # Test length requirements
    assert not validar_password("Sh1")
    assert not validar_password("a" * 129 + "1")

    # Test complexity requirements (new: requires A-Z, a-z, 0-9)
    assert not validar_password("allletters")
    assert not validar_password("ALLUPPERCASE")
    assert not validar_password("12345678")
    assert not validar_password("!@#$%^&*")
    assert not validar_password("lowerand1") # Missing uppercase
    assert not validar_password("UPPERAND1") # Missing lowercase
    assert not validar_password("Upperandlower") # Missing number

    # Test valid passwords
    assert validar_password("Valid123")
    assert validar_password("Password1")
    assert validar_password("1Password")
    assert validar_password("aA1b2c3d4")

def test_validar_password_blocklist():
    # Test expanded blocklist
    assert not validar_password("gamevault123")
    assert not validar_password("GameVault123")
    assert not validar_password("gamevault2024")
    assert not validar_password("gamevault2025")
    assert not validar_password("password123")
    assert not validar_password("Admin123")

def test_validar_password_email_similarity():
    # Email complete matching or containing
    assert not validar_password("juan@gmail.com123A", email="juan@gmail.com")
    assert not validar_password("juan@gmail.com", email="juan@gmail.com")
    assert not validar_password("Somejuan@gmail.comValue", email="juan@gmail.com")

    # Local part matching or containing
    assert not validar_password("Juan12345", email="juan@gmail.com")
    assert not validar_password("SomejuanValue123", email="juan@gmail.com")
    assert not validar_password("JUAN123456", email="juan@example.co.uk")

    # Short local part should not trigger rejection of valid patterns
    # (e.g. if local part is "abc", a password like "Valid123" containing "abc" is okay)
    assert validar_password("Validabc123", email="abc@gmail.com")

    # Valid password that does not contain email or its local part
    assert validar_password("SecurePass123!", email="juan@gmail.com")
