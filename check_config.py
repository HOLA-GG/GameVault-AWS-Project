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
    print(f"  - SHOW_RESET_DEBUG_TOKEN: {app.config.get('SHOW_RESET_DEBUG_TOKEN')}")
    print(f"  - SECRET_KEY: {'[SET]' if app.config.get('SECRET_KEY') else '[MISSING]'}")
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
        is_neon = 'neon' in db_url or 'neon.tech' in db_url
        is_pooler = '-pooler' in db_url
        use_nullpool = app.config.get('DB_USE_NULLPOOL') or is_pooler

        print(f"  - Neon Database Detected: {is_neon}")
        print(f"  - Pooled Host Detected (-pooler): {is_pooler}")
        print(f"  - DB_USE_NULLPOOL Configured: {app.config.get('DB_USE_NULLPOOL')}")
        print(f"  - Effective NullPool Active: {use_nullpool} (Expected Class: NullPool if True, QueuePool/StaticPool if False)")

        if not use_nullpool:
            print(f"    -> Connection Pool Settings (QueuePool):")
            print(f"       * DB_POOL_SIZE: {app.config.get('DB_POOL_SIZE')}")
            print(f"       * DB_MAX_OVERFLOW: {app.config.get('DB_MAX_OVERFLOW')}")
            print(f"       * DB_POOL_RECYCLE: {app.config.get('DB_POOL_RECYCLE')}s")
            print(f"       * DB_POOL_TIMEOUT: {app.config.get('DB_POOL_TIMEOUT')}s")
            if is_neon:
                print("    -> [TIP] Since you are using a Neon database on Render, consider setting DB_USE_NULLPOOL=true")
                print("            or using a pooled connection string (with '-pooler') to delegate connection pooling")
                print("            to Neon's PgBouncer, preventing connection leaks and limit exhaustion.")
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

print("=" * 60)
print("INFRASTRUCTURE VERIFICATION COMPLETE")
print("=" * 60)
