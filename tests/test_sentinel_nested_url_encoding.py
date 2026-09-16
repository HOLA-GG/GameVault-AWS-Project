import os
import pytest
from flask import Flask
from app.models import obtener_key_desde_url
from app.routes import is_valid_presigned_image_url

def test_nested_url_encoding_traversal_key_extraction():
    os.environ['R2_BUCKET_NAME'] = 'my-bucket'

    # Nested encoded url that decodes to pointing to secrets.json:
    # "https://my-bucket.s3.amazonaws.com/covers/%252e%252e%252fsecrets.json"
    # Decodes first to "https://my-bucket.s3.amazonaws.com/covers/%2e%2e/secrets.json"
    # Decodes second to "https://my-bucket.s3.amazonaws.com/covers/../secrets.json"
    nested_url = "https://my-bucket.s3.amazonaws.com/covers/%252e%252e%252fsecrets.json"

    key = obtener_key_desde_url(nested_url)
    assert key is None, f"Expected None for nested traversal URL, but got {key}"

def test_nested_url_encoding_traversal_route_validation():
    app = Flask(__name__)
    app.config['STORAGE_BACKEND'] = 's3'
    app.config['S3_BUCKET_NAME'] = 'my-bucket'
    app.config['S3_REGION'] = 'us-east-1'

    with app.app_context():
        nested_url = "https://my-bucket.s3.us-east-1.amazonaws.com/covers/%252e%252e%252fsecrets.json"
        assert is_valid_presigned_image_url(nested_url) is False

def test_nested_url_encoding_traversal_local_validation():
    app = Flask(__name__)
    app.config['STORAGE_BACKEND'] = 'local'
    app.config['LOCAL_UPLOAD_URL_PATH'] = '/static/uploads'

    with app.app_context():
        # A nested traversal that escapes /static/uploads/
        nested_url = "/static/uploads/covers/%252e%252e%252f%252e%252e%252fsecrets.json"
        assert is_valid_presigned_image_url(nested_url) is False
