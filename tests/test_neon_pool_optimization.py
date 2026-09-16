import os
import unittest
from unittest import mock
from sqlalchemy.pool import NullPool, QueuePool
import app.models

class TestNeonPoolOptimization(unittest.TestCase):
    def setUp(self):
        # Save original engine and database URL state
        self.orig_engine = app.models._engine
        self.orig_database_url = app.models.DATABASE_URL
        app.models._engine = None

    def tearDown(self):
        # Restore original engine and database URL state
        app.models._engine = self.orig_engine
        app.models.DATABASE_URL = self.orig_database_url

    def test_default_pool_setup(self):
        # By default, sqlite uses StaticPool or QueuePool depending on memory
        app.models.DATABASE_URL = "sqlite+pysqlite:///test_temp_default.db"
        with mock.patch.dict(os.environ, {"DB_USE_NULLPOOL": "false"}):
            engine = app.models.get_engine()
            # On SQLite it doesn't use NullPool
            self.assertNotEqual(engine.pool.__class__, NullPool)

    def test_postgres_default_pool_setup(self):
        # Postgres URL without pooler and DB_USE_NULLPOOL=false uses QueuePool
        app.models.DATABASE_URL = "postgresql+psycopg://user:pass@ep-some-db.us-east-1.aws.neon.tech/dbname?sslmode=require"
        with mock.patch.dict(os.environ, {"DB_USE_NULLPOOL": "false"}):
            engine = app.models.get_engine()
            self.assertEqual(engine.pool.__class__, QueuePool)

    def test_postgres_with_use_nullpool_env(self):
        # Postgres URL with DB_USE_NULLPOOL=true uses NullPool
        app.models.DATABASE_URL = "postgresql+psycopg://user:pass@ep-some-db.us-east-1.aws.neon.tech/dbname?sslmode=require"
        with mock.patch.dict(os.environ, {"DB_USE_NULLPOOL": "true"}):
            engine = app.models.get_engine()
            self.assertEqual(engine.pool.__class__, NullPool)

    def test_postgres_with_pooler_host_auto_detect(self):
        # Postgres URL with -pooler in hostname auto-detects and uses NullPool
        app.models.DATABASE_URL = "postgresql+psycopg://user:pass@ep-some-db-pooler.us-east-1.aws.neon.tech/dbname?sslmode=require"
        with mock.patch.dict(os.environ, {"DB_USE_NULLPOOL": "false"}):
            engine = app.models.get_engine()
            self.assertEqual(engine.pool.__class__, NullPool)

    def test_postgres_with_app_config_nullpool(self):
        # Postgres URL using Flask app context config DB_USE_NULLPOOL=True uses NullPool
        from app import create_app
        flask_app = create_app()
        flask_app.config['DB_USE_NULLPOOL'] = True
        app.models.DATABASE_URL = "postgresql+psycopg://user:pass@ep-some-db.us-east-1.aws.neon.tech/dbname?sslmode=require"
        with flask_app.app_context():
            with mock.patch.dict(os.environ, {"DB_USE_NULLPOOL": "false"}):
                engine = app.models.get_engine()
                self.assertEqual(engine.pool.__class__, NullPool)
