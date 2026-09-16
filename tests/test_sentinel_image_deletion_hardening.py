import os
import pytest
from app.models import eliminar_imagen_s3, get_session_factory, ensure_tables
from flask import Flask

@pytest.fixture
def app_with_local_storage(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('STORAGE_BACKEND', 'local')
    monkeypatch.setenv('LOCAL_UPLOAD_DIR', '/tmp/gamevault_test_uploads')
    monkeypatch.setenv('LOCAL_UPLOAD_URL_PATH', '/static/uploads')

    app = Flask(__name__)
    app.config['STORAGE_BACKEND'] = 'local'
    app.config['LOCAL_UPLOAD_DIR'] = '/tmp/gamevault_test_uploads'
    app.config['LOCAL_UPLOAD_URL_PATH'] = '/static/uploads'

    # Ensure upload directory exists
    os.makedirs('/tmp/gamevault_test_uploads/covers', exist_ok=True)
    os.makedirs('/tmp/gamevault_test_uploads-sibling', exist_ok=True)

    yield app

    # Cleanup test files
    import shutil
    try:
        shutil.rmtree('/tmp/gamevault_test_uploads', ignore_errors=True)
        shutil.rmtree('/tmp/gamevault_test_uploads-sibling', ignore_errors=True)
    except:
        pass

def test_eliminar_imagen_s3_path_traversal_prevention(app_with_local_storage):
    """Verifies that eliminar_imagen_s3 blocks path traversal and prefix-only/sibling directory deletions."""
    with app_with_local_storage.app_context():
        # Create a dummy file inside the safe upload folder
        safe_file_path = '/tmp/gamevault_test_uploads/covers/test.png'
        with open(safe_file_path, 'w') as f:
            f.write('dummy-image-content')
        assert os.path.exists(safe_file_path)

        # Create a sibling file in a prefix-overlapping folder (potential partial path traversal bypass)
        sibling_file_path = '/tmp/gamevault_test_uploads-sibling/secret.txt'
        with open(sibling_file_path, 'w') as f:
            f.write('sensitive-sibling-data')
        assert os.path.exists(sibling_file_path)

        # Create an out-of-bounds file (parent directory escape)
        out_of_bounds_file_path = '/tmp/gamevault_test_parent_escape.txt'
        with open(out_of_bounds_file_path, 'w') as f:
            f.write('system-level-file')
        assert os.path.exists(out_of_bounds_file_path)

        try:
            # 1. Attempt sibling path traversal using relative paths
            sibling_traversal_url = '/static/uploads/../gamevault_test_uploads-sibling/secret.txt'
            result = eliminar_imagen_s3(sibling_traversal_url)
            assert result is True # Returns true since it parsed but should NOT delete the sibling file
            assert os.path.exists(sibling_file_path) is True # Sibling file is NOT deleted!

            # 2. Attempt parent directory escape
            parent_escape_url = '/static/uploads/../../gamevault_test_parent_escape.txt'
            result2 = eliminar_imagen_s3(parent_escape_url)
            assert result2 is True
            assert os.path.exists(out_of_bounds_file_path) is True # Out-of-bounds file is NOT deleted!

            # 3. Valid deletion of the safe file
            safe_url = '/static/uploads/covers/test.png'
            result3 = eliminar_imagen_s3(safe_url)
            assert result3 is True
            assert os.path.exists(safe_file_path) is False # Safe file is successfully deleted!

        finally:
            if os.path.exists(out_of_bounds_file_path):
                os.remove(out_of_bounds_file_path)
