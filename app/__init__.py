"""Inicialización principal de la aplicación Flask."""

from __future__ import annotations

import logging
import os
import uuid
from datetime import timedelta

from flask import Flask, g, request
from flask_wtf.csrf import CSRFError
from sentry_sdk import init as init_sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from werkzeug.middleware.proxy_fix import ProxyFix

from app.extensions import csrf, limiter, mail


def env_bool(name: str, default: bool = False) -> bool:
    """Convierte variables de entorno comunes a booleano."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def env_int(name: str, default: int) -> int:
    """Lee enteros desde variables de entorno con fallback seguro."""
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def get_email_config() -> dict:
    """Configuración SMTP preparada para SES u otro proveedor transaccional."""
    return {
        'MAIL_SERVER': os.environ.get('MAIL_SERVER', 'email-smtp.us-east-1.amazonaws.com'),
        'MAIL_PORT': env_int('MAIL_PORT', 587),
        'MAIL_USE_TLS': env_bool('MAIL_USE_TLS', True),
        'MAIL_USE_SSL': env_bool('MAIL_USE_SSL', False),
        'MAIL_USERNAME': os.environ.get('MAIL_USERNAME', ''),
        'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD', ''),
        'MAIL_DEFAULT_SENDER': os.environ.get(
            'MAIL_DEFAULT_SENDER',
            'GameVault <noreply@gamevault.app>',
        ),
        'MAIL_SUPPRESS_SEND': env_bool('MAIL_SUPPRESS_SEND', False),
    }


def configure_logging(app: Flask) -> None:
    """Configura logging consistente para desarrollo y producción."""
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    formatter = logging.Formatter(
        '%(asctime)s level=%(levelname)s logger=%(name)s request_id=%(request_id)s message=%(message)s'
    )

    class RequestFormatter(logging.Formatter):
        def format(self, record):
            if not hasattr(record, 'request_id'):
                record.request_id = getattr(g, 'request_id', '-')
            return super().format(record)

    handler = logging.StreamHandler()
    handler.setFormatter(RequestFormatter(formatter._fmt))

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False


def configure_sentry(app: Flask) -> None:
    """Activa Sentry solo cuando hay DSN configurado."""
    sentry_dsn = os.environ.get('SENTRY_DSN', '').strip()
    if not sentry_dsn:
        return

    init_sentry_sdk(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
        environment=app.config['APP_ENV'],
    )


def build_config() -> dict:
    """Construye la configuración central de la app."""
    app_env = os.environ.get('APP_ENV', 'development').strip().lower()
    secret_key = os.environ.get('SECRET_KEY')

    if not secret_key:
        if app_env == 'production':
            raise RuntimeError('SECRET_KEY es obligatorio en producción.')
        secret_key = 'gamevault-dev-secret-key'

    session_secure_default = app_env == 'production'
    max_upload_mb = env_int('MAX_UPLOAD_MB', 5)
    database_url = os.environ.get('DATABASE_URL', '')
    if app_env == 'testing':
        database_url = database_url or 'sqlite+pysqlite:///gamevault_test.db'
    elif not database_url:
        database_url = 'sqlite+pysqlite:///gamevault_dev.db'

    storage_backend = os.environ.get('STORAGE_BACKEND', 'none').strip().lower() or 'none'
    if database_url.startswith('postgresql'):
        database_backend = 'neon'
    elif database_url.startswith('sqlite'):
        database_backend = 'sqlite'
    else:
        database_backend = 'postgres'

    return {
        'APP_ENV': app_env,
        'SECRET_KEY': secret_key,
        'DATABASE_URL': database_url,
        'DATABASE_BACKEND': database_backend,
        'STORAGE_BACKEND': storage_backend,
        'MAX_CONTENT_LENGTH': max_upload_mb * 1024 * 1024,
        'MAX_UPLOAD_MB': max_upload_mb,
        'MAX_IMAGE_UPLOAD_BYTES': max_upload_mb * 1024 * 1024,
        'SESSION_COOKIE_SECURE': env_bool('SESSION_COOKIE_SECURE', session_secure_default),
        'SESSION_COOKIE_HTTPONLY': env_bool('SESSION_COOKIE_HTTPONLY', True),
        'SESSION_COOKIE_SAMESITE': os.environ.get('SESSION_COOKIE_SAMESITE', 'Lax'),
        'PERMANENT_SESSION_LIFETIME': timedelta(hours=12),
        'PREFERRED_URL_SCHEME': os.environ.get(
            'PREFERRED_URL_SCHEME',
            'https' if app_env == 'production' else 'http',
        ),
        'WTF_CSRF_ENABLED': env_bool('WTF_CSRF_ENABLED', True),
        'WTF_CSRF_TIME_LIMIT': env_int('WTF_CSRF_TIME_LIMIT', 3600),
        'WTF_CSRF_SSL_STRICT': env_bool('WTF_CSRF_SSL_STRICT', app_env == 'production'),
        'RATELIMIT_STORAGE_URI': os.environ.get('RATELIMIT_STORAGE_URI', 'memory://'),
        'RATELIMIT_HEADERS_ENABLED': True,
        'DEFAULT_USER_ID': os.environ.get('DEFAULT_USER_ID', 'user-demo-001'),
        'S3_BUCKET_NAME': os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files'),
        'S3_REGION': os.environ.get('AWS_REGION', 'us-east-1'),
        'RESET_TOKEN_EXPIRY_MINUTES': env_int('RESET_TOKEN_EXPIRY_MINUTES', 30),
        'AUDIT_LOG_RETENTION_DAYS': env_int('AUDIT_LOG_RETENTION_DAYS', 90),
        'GAMES_PER_PAGE': env_int('GAMES_PER_PAGE', 12),
        'ADMIN_USERS_PER_PAGE': env_int('ADMIN_USERS_PER_PAGE', 25),
        'ADMIN_LOGS_PER_PAGE': env_int('ADMIN_LOGS_PER_PAGE', 50),
    }


def create_app() -> Flask:
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)
    app.config.update(build_config())
    app.config.update(get_email_config())
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

    configure_logging(app)
    configure_sentry(app)

    mail.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    @app.before_request
    def assign_request_context() -> None:
        g.request_id = request.headers.get('X-Request-Id') or str(uuid.uuid4())

    @app.after_request
    def log_request(response):
        app.logger.info(
            '%s %s status=%s remote_addr=%s',
            request.method,
            request.path,
            response.status_code,
            request.headers.get('X-Forwarded-For', request.remote_addr),
        )
        response.headers['X-Request-Id'] = g.request_id
        return response

    @app.context_processor
    def inject_app_context():
        return {
            'APP_ENV': app.config['APP_ENV'],
            'MAX_UPLOAD_MB': app.config['MAX_UPLOAD_MB'],
        }

    @app.errorhandler(413)
    def payload_too_large(_error):
        return ('El archivo supera el limite permitido.', 413)

    @app.errorhandler(429)
    def rate_limited(_error):
        return ('Demasiados intentos. Espera un momento e intenta de nuevo.', 429)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        app.logger.warning('csrf_validation_failed reason=%s', error.description)
        return ('Tu formulario expiro o no paso la validacion de seguridad.', 400)

    from app.models import init_database
    from app.routes import main_bp

    init_database()

    app.register_blueprint(main_bp, url_prefix='/')
    return app


app = create_app()
