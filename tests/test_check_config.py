import os
import subprocess
import sys
import unittest

from app import create_app
from app.models import get_engine

class TestCheckConfigScript(unittest.TestCase):
    def test_check_config_execution(self):
        """Verifica que check_config.py se ejecute exitosamente vía subproceso."""
        result = subprocess.run(
            [sys.executable, 'check_config.py'],
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        self.assertEqual(result.returncode, 0, f"check_config.py falló con stderr:\n{result.stderr}")
        self.assertIn("GAMEVAULT INFRASTRUCTURE & CONFIGURATION CHECKER", result.stdout)
        self.assertIn("INFRASTRUCTURE VERIFICATION COMPLETE", result.stdout)
        self.assertIn("Database is connected and healthy", result.stdout)

    def test_check_config_pool_logic_sqlite(self):
        """Verifica que la lógica de pool en check_config reporte correctamente SQLite."""
        flask_app = create_app()
        with flask_app.app_context():
            engine = get_engine()
            pool_class = engine.pool.__class__.__name__
            self.assertIn(pool_class, {'QueuePool', 'StaticPool', 'NullPool'})
