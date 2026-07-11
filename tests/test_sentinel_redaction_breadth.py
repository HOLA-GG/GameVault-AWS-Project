import pytest
from app.models import redact_sensitive_details

def test_redact_breadth_limit_dict():
    # Test dictionary breadth limit
    large_dict = {f"key_{i}": i for i in range(150)}
    redacted = redact_sensitive_details(large_dict)

    assert len(redacted) == 101
    assert redacted['[BREADTH_LIMIT_REACHED]'] == '...'
    assert 'key_0' in redacted
    assert 'key_99' in redacted
    assert 'key_100' not in redacted

def test_redact_breadth_limit_list():
    # Test list breadth limit
    large_list = [i for i in range(150)]
    redacted = redact_sensitive_details(large_list)

    assert len(redacted) == 101
    assert redacted[100] == '[BREADTH_LIMIT_REACHED]'
    assert redacted[0] == 0
    assert redacted[99] == 99

def test_redact_non_serializable():
    # Test non-serializable type handling
    class NonSerializable:
        def __str__(self):
            return "special_object"

    obj = NonSerializable()
    redacted = redact_sensitive_details(obj)
    assert redacted == "special_object"

def test_redact_bytes_handling():
    # Test bytes handling
    raw_bytes = b"hello world"
    redacted = redact_sensitive_details(raw_bytes)
    assert redacted == "hello world"

    # Test bytes with invalid utf-8
    bad_bytes = b"\xff\xfe\xfd"
    redacted = redact_sensitive_details(bad_bytes)
    assert isinstance(redacted, str)

def test_redact_recursive_breadth():
    # Test breadth limit in nested structures
    nested = {
        "inner_list": [i for i in range(150)],
        "inner_dict": {f"k_{i}": i for i in range(150)}
    }
    redacted = redact_sensitive_details(nested)

    assert len(redacted["inner_list"]) == 101
    assert redacted["inner_list"][100] == "[BREADTH_LIMIT_REACHED]"
    assert len(redacted["inner_dict"]) == 101
    assert redacted["inner_dict"]["[BREADTH_LIMIT_REACHED]"] == "..."
