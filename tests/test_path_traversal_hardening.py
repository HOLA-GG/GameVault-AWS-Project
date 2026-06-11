import pytest
from app.routes import is_valid_presigned_image_url
from tests.test_app import app

def test_is_valid_presigned_image_url_local_traversal(app):
    with app.app_context():
        app.config['STORAGE_BACKEND'] = 'local'
        app.config['LOCAL_UPLOAD_URL_PATH'] = '/static/uploads'

        # Valid cases
        assert is_valid_presigned_image_url('/static/uploads/covers/test.jpg') is True
        assert is_valid_presigned_image_url('/static/uploads/test.png') is True

        # Traversal attempts (should be False)
        assert is_valid_presigned_image_url('/static/uploads/../../etc/passwd') is False
        assert is_valid_presigned_image_url('/static/uploads/..%2f..%2fetc/passwd') is False
        assert is_valid_presigned_image_url('/static/uploads/..\\..\\etc/passwd') is False
        assert is_valid_presigned_image_url('/static/uploads/subdir/../hidden.jpg') is True  # Normalized to /static/uploads/hidden.jpg

        # Protocol/Host bypass attempts
        assert is_valid_presigned_image_url('http://evil.com/static/uploads/test.jpg') is False
        assert is_valid_presigned_image_url('//evil.com/static/uploads/test.jpg') is False

        # Directory prefix mismatch
        assert is_valid_presigned_image_url('/static/uploads-backup/test.jpg') is False
        assert is_valid_presigned_image_url('/other/path/test.jpg') is False

def test_is_valid_presigned_image_url_s3(app):
    with app.app_context():
        app.config['STORAGE_BACKEND'] = 's3'
        app.config['S3_BUCKET_NAME'] = 'my-bucket'
        app.config['S3_REGION'] = 'us-east-1'

        valid_url = 'https://my-bucket.s3.us-east-1.amazonaws.com/covers/test.jpg'
        assert is_valid_presigned_image_url(valid_url) is True

        invalid_url = 'https://other-bucket.s3.us-east-1.amazonaws.com/covers/test.jpg'
        assert is_valid_presigned_image_url(invalid_url) is False
