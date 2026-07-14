import pytest
import os
from flask import Flask
from app.models import obtener_key_desde_url
from app.routes import is_valid_presigned_image_url

def test_s3_path_traversal_vulnerability():
    # Setup environment for obtener_key_desde_url
    os.environ['R2_BUCKET_NAME'] = 'my-bucket'

    # Vulnerable URL that uses .. to escape covers/ prefix
    vulnerable_url = "https://my-bucket.s3.amazonaws.com/covers/../secrets.json"

    # Current vulnerable implementation might return "covers/../secrets.json"
    # which starts with "covers/" but points to "secrets.json"
    key = obtener_key_desde_url(vulnerable_url)

    # We expect the hardened version to return None for traversal attempts
    assert key is None or ".." not in key

def test_is_valid_presigned_image_url_s3_traversal():
    app = Flask(__name__)
    app.config['STORAGE_BACKEND'] = 's3'
    app.config['S3_BUCKET_NAME'] = 'my-bucket'
    app.config['S3_REGION'] = 'us-east-1'

    with app.app_context():
        # Vulnerable URL: starts with /covers/ but tries to go up
        vulnerable_url = "https://my-bucket.s3.us-east-1.amazonaws.com/covers/../secrets.json"

        # We expect the hardened version to return False
        assert is_valid_presigned_image_url(vulnerable_url) is False
