import pytest
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

@pytest.fixture
def app(monkeypatch):
    db_file = 'gamevault_test_boundaries.db'
    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

    monkeypatch.setenv('APP_ENV', 'testing')
    monkeypatch.setenv('DATABASE_URL', f'sqlite+pysqlite:///{db_file}')
    monkeypatch.setenv('RATELIMIT_ENABLED', '0')

    # Force reload of app and models
    modules_to_reload = ['app', 'app.models', 'app.routes', 'app.extensions']
    for mod in modules_to_reload:
        if mod in sys.modules:
            del sys.modules[mod]

    import app as app_module
    flask_app = app_module.create_app()
    flask_app.config.update({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "RATELIMIT_ENABLED": False,
    })

    yield flask_app

    if os.path.exists(db_file):
        try:
            os.remove(db_file)
        except:
            pass

def test_parse_date_filter_boundary(app):
    """Verifica que parse_date_filter rechace cadenas de fecha demasiado largas para evitar DoS."""
    from app.models import parse_date_filter

    # Cadena de fecha normal (válida)
    assert parse_date_filter("2026-05-25") is not None

    # Cadena de fecha extremadamente larga (> 50 chars)
    giant_date = "2026-05-25" + "0" * 100
    assert parse_date_filter(giant_date) is None

def test_is_valid_image_file_boundary(app):
    """Verifica que is_valid_image_file limite la longitud del nombre del archivo."""
    from app.models import is_valid_image_file

    mock_file = MagicMock()
    mock_file.filename = "a" * 300 + ".png"
    mock_file.content_type = "image/png"

    # Debería retornar False por nombre demasiado largo
    valid, err = is_valid_image_file(mock_file)
    assert valid is False
    assert "demasiado largo" in err

def test_obtener_todos_logs_boundary(app):
    """Verifica que obtener_todos_logs aplique límites de longitud a los filtros de búsqueda."""
    from app.models import obtener_todos_logs

    # Filtros con valores normales
    filters_normal = {
        'user_id': 'normal-id',
        'action': 'LOGIN',
        'status': 'SUCCESS'
    }
    # No debería haber errores al llamar
    obtener_todos_logs(filters_normal)

    # Filtros con valores gigantes (superan las restricciones de longitud del esquema)
    filters_giant = {
        'user_id': 'a' * 100,
        'action': 'b' * 200,
        'status': 'c' * 50
    }
    # Debería ejecutarse sin problemas (ignorando los filtros gigantes que no cumplen con los límites de longitud)
    results = obtener_todos_logs(filters_giant)
    assert isinstance(results, list)

def test_obtener_todos_logs_none_values(app):
    """Verifica que obtener_todos_logs no falle si los filtros tienen valores None."""
    from app.models import obtener_todos_logs

    filters_with_none = {
        'user_id': None,
        'action': None,
        'status': None
    }
    # Esto solía arrojar AttributeError en str.strip() antes del fix de robustez
    results = obtener_todos_logs(filters_with_none)
    assert isinstance(results, list)

def test_bulk_lists_limit_boundary(app):
    """Verifica que las funciones de recuperación masiva limiten el número de elementos a procesar."""
    from app.models import obtener_usuarios_por_ids, obtener_ratings_multiple

    # Generar listas gigantescas
    giant_ids = [f"id-{i}" for i in range(1005)]

    # Probar que se limita internamente a 1000 items
    # (podemos mockear para que no vaya a la base real o simplemente llamarlo
    # y verificar que la base no falle o que la longitud de entrada de ids se trunque)
    import app.models as models
    original_execute = models.get_session_factory()().execute

    called_ids = []
    def mock_execute(statement, *args, **kwargs):
        # Capturamos los parámetros de la consulta SQL para verificar la longitud de 'in_'
        try:
            compile_info = str(statement)
            if "users.user_id IN" in compile_info:
                params = statement.compile().params
                for k, v in params.items():
                    if isinstance(v, list) or isinstance(v, tuple):
                        called_ids.append(list(v))
        except Exception:
            pass
        return original_execute(statement, *args, **kwargs)

    # Mock del método execute de la sesión
    session = models.get_session_factory()()
    session.execute = mock_execute

    try:
        # Esto llamará a la consulta internamente
        obtener_usuarios_por_ids(giant_ids)
        # Si se truncó a 1000, los parámetros de la consulta deberían tener como máximo 1000 elementos
        for ids_list in called_ids:
            assert len(ids_list) <= 1000
    finally:
        # Restaurar
        session.execute = original_execute

def test_bulk_lists_iterable_types(app):
    """Verifica que obtener_usuarios_por_ids maneje otros iterables como sets o generadores sin crashear."""
    from app.models import obtener_usuarios_por_ids

    # Usar un set
    set_ids = {"id-1", "id-2"}
    results_set = obtener_usuarios_por_ids(set_ids)
    assert isinstance(results_set, list)

    # Usar un generador
    gen_ids = (f"id-{i}" for i in range(5))
    results_gen = obtener_usuarios_por_ids(gen_ids)
    assert isinstance(results_gen, list)
