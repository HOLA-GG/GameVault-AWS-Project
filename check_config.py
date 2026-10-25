import os
import sys
from urllib.parse import urlparse

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app
from app.models import get_engine, database_healthcheck

print("=" * 60)
print("GAMEVAULT INFRASTRUCTURE & CONFIGURATION CHECKER")
print("=" * 60)

try:
    app = create_app()
except Exception as e:
    print(f"ERROR: Failed to initialize Flask application context. Details: {e}")
    sys.exit(1)

with app.app_context():
    # 1. Environment & Basic Settings
    print("[1] Environment Settings:")
    print(f"  - APP_ENV: {app.config.get('APP_ENV')}")
    print(f"  - LOG_LEVEL: {os.environ.get('LOG_LEVEL', 'INFO')}")
    print(f"  - WEB_CONCURRENCY: {app.config.get('WEB_CONCURRENCY')}")
    print(f"  - PREFERRED_URL_SCHEME: {app.config.get('PREFERRED_URL_SCHEME')}")
    print(f"  - SHOW_RESET_DEBUG_TOKEN: {app.config.get('SHOW_RESET_DEBUG_TOKEN')}")
    print(f"  - SECRET_KEY: {'[SET]' if app.config.get('SECRET_KEY') else '[MISSING]'}")
    is_render = bool(os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'))
    print(f"  - Render Platform Detected: {is_render}")
    print()

    # 2. Database Settings & Connection Checking
    print("[2] Database & Connection Settings:")
    db_url = app.config.get('DATABASE_URL', '')
    if db_url:
        try:
            parsed = urlparse(db_url)
            if parsed.password:
                safe_url = db_url.replace(parsed.password, '********')
            else:
                safe_url = db_url
        except Exception:
            safe_url = '[UNPARSABLE]'
    else:
        safe_url = '[NOT CONFIGURED]'

    print(f"  - DATABASE_URL: {safe_url}")
    print(f"  - DATABASE_BACKEND: {app.config.get('DATABASE_BACKEND')}")
    print(f"  - NEON_PROJECT_ID: {app.config.get('NEON_PROJECT_ID') or '[NOT SET]'}")
    print(f"  - NEON_SSLMODE: {app.config.get('NEON_SSLMODE')}")

    # Check database connectivity
    print("  - Verifying database connection healthcheck...")
    db_healthy = database_healthcheck()
    if db_healthy:
        print("    -> [OK] Database is connected and healthy.")
    else:
        print("    -> [WARNING/ERROR] Database connection failed or could not be established.")

    # Retrieve engine pool details
    try:
        engine = get_engine()
        pool_class_name = engine.pool.__class__.__name__
        print(f"  - SQLAlchemy Engine Pool Class: {pool_class_name}")

        # Check pool parameters
        is_neon = 'neon' in db_url or 'neon.tech' in db_url or app.config.get('DATABASE_BACKEND') == 'neon' or bool(app.config.get('NEON_PROJECT_ID'))
        is_pooler = '-pooler' in db_url
        is_sqlite = db_url.startswith('sqlite')
        use_nullpool = (app.config.get('DB_USE_NULLPOOL') or is_pooler) and not is_sqlite

        print(f"  - Neon Database Detected: {is_neon}")
        print(f"  - Pooled Host Detected (-pooler): {is_pooler}")
        print(f"  - DB_USE_NULLPOOL Configured: {app.config.get('DB_USE_NULLPOOL')}")
        print(f"  - Effective NullPool Active: {pool_class_name == 'NullPool'} (Class: {pool_class_name})")

        if pool_class_name != 'NullPool':
            print(f"    -> Connection Pool Settings ({pool_class_name}):")
            if not is_sqlite:
                print(f"       * DB_POOL_SIZE: {app.config.get('DB_POOL_SIZE')}")
                print(f"       * DB_MAX_OVERFLOW: {app.config.get('DB_MAX_OVERFLOW')}")
                print(f"       * DB_POOL_RECYCLE: {app.config.get('DB_POOL_RECYCLE')}s")
                print(f"       * DB_POOL_TIMEOUT: {app.config.get('DB_POOL_TIMEOUT')}s")
                if is_neon:
                    print("    -> [TIP] Since you are using a Neon database on Render, consider setting DB_USE_NULLPOOL=true")
                    print("            or using a pooled connection string (with '-pooler') to delegate connection pooling")
                    print("            to Neon's PgBouncer, preventing connection leaks and limit exhaustion.")
            else:
                print("    -> [INFO] SQLite detected; SQLite manages its own internal pool (StaticPool / QueuePool).")
        else:
            print("    -> [OK] NullPool active: Connection pooling delegated directly to Neon PgBouncer.")
    except Exception as e:
        print(f"  - [ERROR] Could not inspect SQLAlchemy Engine details: {e}")
    print()

    # 3. Storage Settings
    print("[3] Storage Settings:")
    print(f"  - STORAGE_BACKEND: {app.config.get('STORAGE_BACKEND')}")
    print(f"  - DIRECT_UPLOADS_ENABLED: {app.config.get('DIRECT_UPLOADS_ENABLED')}")
    if app.config.get('STORAGE_BACKEND') in {'r2', 's3'}:
        print(f"  - S3_BUCKET_NAME: {app.config.get('S3_BUCKET_NAME')}")
        print(f"  - R2_ACCOUNT_ID: {'[SET]' if app.config.get('R2_ACCOUNT_ID') else '[NOT SET]'}")
        print(f"  - R2_ENDPOINT_URL: {app.config.get('R2_ENDPOINT_URL') or '[NOT SET]'}")
    else:
        print(f"  - LOCAL_UPLOAD_DIR: {app.config.get('LOCAL_UPLOAD_DIR')}")
        print(f"  - LOCAL_UPLOAD_URL_PATH: {app.config.get('LOCAL_UPLOAD_URL_PATH')}")
    print()

    # 4. Email Settings
    print("[4] Email Settings:")
    print(f"  - MAIL_SERVER: {app.config.get('MAIL_SERVER')}")
    print(f"  - MAIL_PORT: {app.config.get('MAIL_PORT')}")
    print(f"  - MAIL_USE_TLS: {app.config.get('MAIL_USE_TLS')}")
    print(f"  - MAIL_USE_SSL: {app.config.get('MAIL_USE_SSL')}")
    print(f"  - MAIL_SUPPRESS_SEND: {app.config.get('MAIL_SUPPRESS_SEND')}")
    print(f"  - MAIL_DEFAULT_SENDER: {app.config.get('MAIL_DEFAULT_SENDER')}")
    print()

    # 5. Security & Session Settings
    print("[5] Security & Session Settings:")
    print(f"  - SESSION_COOKIE_NAME: {app.config.get('SESSION_COOKIE_NAME')}")
    print(f"  - SESSION_COOKIE_SECURE: {app.config.get('SESSION_COOKIE_SECURE')}")
    print(f"  - SESSION_COOKIE_HTTPONLY: {app.config.get('SESSION_COOKIE_HTTPONLY')}")
    print(f"  - SESSION_COOKIE_SAMESITE: {app.config.get('SESSION_COOKIE_SAMESITE')}")
    print(f"  - WTF_CSRF_ENABLED: {app.config.get('WTF_CSRF_ENABLED')}")
    print(f"  - WTF_CSRF_SSL_STRICT: {app.config.get('WTF_CSRF_SSL_STRICT')}")
    print()

    # 6. Limits, Pagination, Monitoring & Retention Settings
    print("[6] Limits, Pagination, Monitoring & Retention Settings:")
    print(f"  - RATELIMIT_STORAGE_URI: {app.config.get('RATELIMIT_STORAGE_URI')}")
    print(f"  - MAX_UPLOAD_MB: {app.config.get('MAX_UPLOAD_MB')}MB")
    print(f"  - GAMES_PER_PAGE: {app.config.get('GAMES_PER_PAGE')}")
    print(f"  - ADMIN_USERS_PER_PAGE: {app.config.get('ADMIN_USERS_PER_PAGE')}")
    print(f"  - ADMIN_LOGS_PER_PAGE: {app.config.get('ADMIN_LOGS_PER_PAGE')}")
    print(f"  - RESET_TOKEN_EXPIRY_MINUTES: {app.config.get('RESET_TOKEN_EXPIRY_MINUTES')} minutes")
    print(f"  - AUDIT_LOG_RETENTION_DAYS: {app.config.get('AUDIT_LOG_RETENTION_DAYS')} days")
    print(f"  - SENTRY_DSN: {'[SET]' if os.environ.get('SENTRY_DSN') else '[NOT SET]'}")
    print(f"  - SENTRY_TRACES_SAMPLE_RATE: {os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.0')}")
    print()

    # 7. Render & Neon Platform Audit Summary
    print("[7] Render & Neon Optimization Audit Summary:")
    app_env = app.config.get('APP_ENV')
    is_prod = app_env == 'production'

    # Check PostgreSQL / psycopg driver normalization
    if db_url.startswith(('postgres', 'postgresql')):
        if '+psycopg' in db_url:
            print("  - [OK] Database driver: SQLAlchemy 2.0+ psycopg driver configured.")
        else:
            print("  - [INFO] Database driver: Standard postgresql URL automatically normalized to psycopg at runtime.")

        if 'sslmode=' in db_url:
            print("  - [OK] SSL Transport: sslmode explicitly specified in DATABASE_URL.")
        else:
            print(f"  - [OK] SSL Transport: NEON_SSLMODE='{app.config.get('NEON_SSLMODE')}' enforced by runtime normalizer.")

        if use_nullpool or pool_class_name == 'NullPool':
            print("  - [OK] Connection Pooling: NullPool active (delegating pooling to Neon PgBouncer).")
        else:
            print("  - [WARNING] Connection Pooling: QueuePool active. For Neon serverless PostgreSQL on Render, NullPool is recommended.")
    else:
        print(f"  - [INFO] Non-Postgres backend active ({app.config.get('DATABASE_BACKEND')}). Database pooling checks skipped.")

    if is_prod:
        if app.config.get('SESSION_COOKIE_SECURE') and app.config.get('WTF_CSRF_SSL_STRICT'):
            print("  - [OK] Security Hardening: SSL Strict CSRF and Secure Session Cookies enabled for production on Render.")
        else:
            print("  - [WARNING] Security Hardening: Ensure SESSION_COOKIE_SECURE=true and WTF_CSRF_SSL_STRICT=true in production.")

        if app.config.get('WEB_CONCURRENCY', 1) >= 2:
            print(f"  - [OK] Gunicorn Concurrency: WEB_CONCURRENCY={app.config.get('WEB_CONCURRENCY')} optimal for Render instances.")
        else:
            print(f"  - [TIP] Gunicorn Concurrency: WEB_CONCURRENCY={app.config.get('WEB_CONCURRENCY')}. Consider setting WEB_CONCURRENCY=2 for Render.")
    else:
        print(f"  - [INFO] Application running in '{app_env}' mode.")

print("=" * 60)
print("INFRASTRUCTURE VERIFICATION COMPLETE")
print("=" * 60)
