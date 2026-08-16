"""Inicialización principal de la aplicación Flask."""

from __future__ import annotations

import base64
import logging
import os
import uuid
from datetime import timedelta

from flask import Flask, g, request, session
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
                try:
                    record.request_id = getattr(g, 'request_id', '-')
                except RuntimeError:
                    record.request_id = '-'
            return super().format(record)

    handler = logging.StreamHandler()
    handler.setFormatter(RequestFormatter(formatter._fmt))

    app.logger.handlers.clear()
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False


def configure_sentry(app: Flask) -> None:
    """Activa Sentry solo cuando hay DSN configurado con filtrado de seguridad."""
    sentry_dsn = os.environ.get('SENTRY_DSN', '').strip()
    if not sentry_dsn:
        return

    from app.models import redact_sensitive_details

    def before_send(event, hint):
        try:
            # Prevents leaking passwords, hashes, tokens, and PII to Sentry (Security hardening)
            return redact_sensitive_details(event)
        except Exception:
            return event

    init_sentry_sdk(
        dsn=sentry_dsn,
        integrations=[FlaskIntegration()],
        traces_sample_rate=float(os.environ.get('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
        environment=app.config['APP_ENV'],
        before_send=before_send,
    )


def build_config() -> dict:
    """Construye la configuración central de la app."""
    app_env = os.environ.get('APP_ENV', 'development').strip().lower()
    app_root = os.path.dirname(os.path.abspath(__file__))
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
    local_upload_dir = os.environ.get('LOCAL_UPLOAD_DIR') or os.path.join(app_root, 'static', 'uploads')
    local_upload_url_path = os.environ.get('LOCAL_UPLOAD_URL_PATH', '/static/uploads').rstrip('/')
    direct_uploads_enabled = storage_backend not in {'none', 'local'}
    show_reset_debug_token = env_bool('SHOW_RESET_DEBUG_TOKEN', app_env == 'development')
    bootstrap_admin_enabled = env_bool('BOOTSTRAP_ADMIN_ENABLED', app_env == 'development')
    bootstrap_admin_email = os.environ.get(
        'BOOTSTRAP_ADMIN_EMAIL',
        'admin@gamevault' if app_env == 'development' else '',
    )
    bootstrap_admin_password = os.environ.get(
        'BOOTSTRAP_ADMIN_PASSWORD',
        '12345678' if app_env == 'development' else '',
    )
    if database_url.startswith('postgresql'):
        database_backend = 'neon'
    elif database_url.startswith('sqlite'):
        database_backend = 'sqlite'
    else:
        database_backend = 'postgres'

    session_cookie_secure = env_bool('SESSION_COOKIE_SECURE', session_secure_default)
    session_cookie_name = '__Host-session' if session_cookie_secure else 'session'

    return {
        'APP_ENV': app_env,
        'SECRET_KEY': secret_key,
        'DATABASE_URL': database_url,
        'DATABASE_BACKEND': database_backend,
        'STORAGE_BACKEND': storage_backend,
        'LOCAL_UPLOAD_DIR': local_upload_dir,
        'LOCAL_UPLOAD_URL_PATH': local_upload_url_path,
        'DIRECT_UPLOADS_ENABLED': direct_uploads_enabled,
        'SHOW_RESET_DEBUG_TOKEN': show_reset_debug_token,
        'BOOTSTRAP_ADMIN_ENABLED': bootstrap_admin_enabled,
        'BOOTSTRAP_ADMIN_EMAIL': bootstrap_admin_email,
        'BOOTSTRAP_ADMIN_PASSWORD': bootstrap_admin_password,
        'BOOTSTRAP_ADMIN_NAME': os.environ.get('BOOTSTRAP_ADMIN_NAME', 'GameVault'),
        'BOOTSTRAP_ADMIN_LAST_NAME': os.environ.get('BOOTSTRAP_ADMIN_LAST_NAME', 'Admin'),
        'MAX_CONTENT_LENGTH': max_upload_mb * 1024 * 1024,
        'MAX_UPLOAD_MB': max_upload_mb,
        'MAX_IMAGE_UPLOAD_BYTES': max_upload_mb * 1024 * 1024,
        'SESSION_COOKIE_SECURE': session_cookie_secure,
        'SESSION_COOKIE_NAME': session_cookie_name,
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
        'S3_BUCKET_NAME': os.environ.get('R2_BUCKET_NAME') or os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files'),
        'S3_REGION': os.environ.get('AWS_REGION', 'us-east-1'),
        'R2_ACCOUNT_ID': os.environ.get('R2_ACCOUNT_ID'),
        'R2_ENDPOINT_URL': os.environ.get('R2_ENDPOINT_URL'),
        'RESET_TOKEN_EXPIRY_MINUTES': env_int('RESET_TOKEN_EXPIRY_MINUTES', 30),
        'AUDIT_LOG_RETENTION_DAYS': env_int('AUDIT_LOG_RETENTION_DAYS', 90),
        'DB_USE_NULLPOOL': env_bool('DB_USE_NULLPOOL', False),
        'DB_POOL_SIZE': env_int('DB_POOL_SIZE', 5),
        'DB_MAX_OVERFLOW': env_int('DB_MAX_OVERFLOW', 10),
        'DB_POOL_RECYCLE': env_int('DB_POOL_RECYCLE', 280),
        'DB_POOL_TIMEOUT': env_int('DB_POOL_TIMEOUT', 30),
        'GAMES_PER_PAGE': env_int('GAMES_PER_PAGE', 12),
        'ADMIN_USERS_PER_PAGE': env_int('ADMIN_USERS_PER_PAGE', 25),
        'ADMIN_LOGS_PER_PAGE': env_int('ADMIN_LOGS_PER_PAGE', 50),
    }


def create_app() -> Flask:
    """Crea y configura la aplicación Flask."""
    app = Flask(__name__)
    app.config.update(build_config())
    app.config.update(get_email_config())
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    configure_logging(app)
    configure_sentry(app)

    mail.init_app(app)
    csrf.init_app(app)

    limiter.init_app(app)

    @app.before_request
    def assign_request_context() -> None:
        req_id = request.headers.get('X-Request-Id') or ''
        # Limit the length of custom request IDs to prevent memory-based DoS (Security hardening)
        if len(req_id) > 100:
            req_id = req_id[:100]
        g.request_id = req_id or str(uuid.uuid4())
        # Generate cryptographic nonce for CSP (Security hardening)
        g.csp_nonce = base64.b64encode(os.urandom(16)).decode('utf-8')

    @app.after_request
    def log_request(response):
        request_id = getattr(g, 'request_id', str(uuid.uuid4()))
        log_path = request.path
        # Avoid leaking sensitive tokens in audit logs (defense-in-depth)
        if log_path.startswith('/reset-password/'):
            log_path = '/reset-password/[REDACTED]'

        app.logger.info(
            '%s %s status=%s remote_addr=%s',
            request.method,
            log_path,
            response.status_code,
            request.remote_addr,
        )
        response.headers['X-Request-Id'] = request_id
        response.headers['X-Content-Type-Options'] = 'nosniff'
        # Prevent clickjacking
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        # Legacy XSS protection for older browsers
        response.headers['X-XSS-Protection'] = '1; mode=block'
        # Prevent Adobe Flash/PDF cross-domain leaks
        response.headers['X-Permitted-Cross-Domain-Policies'] = 'none'
        # Prevent cross-origin window leaks (defense-in-depth for social/auth)
        response.headers['Cross-Origin-Opener-Policy'] = 'same-origin'
        # Prevent cross-origin resource sharing risks
        response.headers['Cross-Origin-Resource-Policy'] = 'same-origin'

        # Disable caching and indexing for sensitive authenticated routes (Security enhancement)
        sensitive_endpoints = {
            'main.dashboard', 'main.profile', 'main.admin_panel',
            'main.admin_collections', 'main.admin_logs', 'main.editar_juego_ruta',
            'main.admin_logs_export', 'main.admin_logs_clear',
            'main.forgot_password', 'main.forgot_password_manual',
            'main.validate_token_page', 'main.verify_token',
            'main.reset_password_with_email', 'main.healthz', 'main.salud'
        }
        if request.endpoint in sensitive_endpoints:
            response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'

            # Harden Referrer-Policy for authentication routes containing tokens/PII (Security enhancement)
            auth_sensitive_endpoints = {
                'main.forgot_password', 'main.forgot_password_manual',
                'main.validate_token_page', 'main.reset_password_with_email'
            }
            if request.endpoint in auth_sensitive_endpoints:
                response.headers['Referrer-Policy'] = 'no-referrer'

        # Enforce HTTPS in production
        if app.config.get('APP_ENV') == 'production':
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'

        # Minimize attack surface by disabling unused browser features
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=(), payment=(), usb=(), bluetooth=(), hid=(), serial=()'

        # Harden CSP by restricting S3/R2 access to the specific bucket host (Security enhancement)
        img_sources = ["'self'", "data:", "blob:"]
        connect_sources = ["'self'"]
        storage_backend = app.config.get('STORAGE_BACKEND')
        if storage_backend and storage_backend not in {'none', 'local'}:
            bucket = app.config.get('S3_BUCKET_NAME')
            region = app.config.get('S3_REGION')
            r2_endpoint = app.config.get('R2_ENDPOINT_URL')
            r2_account_id = app.config.get('R2_ACCOUNT_ID')

            if storage_backend == 'r2':
                if r2_endpoint:
                    r2_host = urlparse(r2_endpoint).netloc
                elif r2_account_id:
                    r2_host = f"{r2_account_id}.r2.cloudflarestorage.com"
                else:
                    r2_host = None

                if r2_host:
                    img_sources.append(r2_host)
                    connect_sources.append(r2_host)
            else:
                if bucket and region:
                    s3_host = f"{bucket}.s3.{region}.amazonaws.com"
                    img_sources.append(s3_host)
                    connect_sources.append(s3_host)

        # Content-Security-Policy: defense-in-depth against XSS and injection
        csp_nonce = getattr(g, 'csp_nonce', '')
        csp_parts = [
            "default-src 'self'",
            f"script-src 'self' 'nonce-{csp_nonce}'",
            "style-src 'self' 'unsafe-inline'",
            f"img-src {' '.join(img_sources)}",
            f"connect-src {' '.join(connect_sources)}",
            "frame-src 'none'",
            "font-src 'self'",
            "media-src 'none'",
            "worker-src 'none'",
            "frame-ancestors 'self'",
            "form-action 'self'",
            "base-uri 'self'",
            "object-src 'none'",
            "upgrade-insecure-requests"
        ]
        response.headers['Content-Security-Policy'] = "; ".join(csp_parts)
        return response

    @app.context_processor
    def inject_app_context():
        return {
            'APP_ENV': app.config['APP_ENV'],
            'MAX_UPLOAD_MB': app.config['MAX_UPLOAD_MB'],
            'STORAGE_BACKEND': app.config['STORAGE_BACKEND'],
            'DIRECT_UPLOADS_ENABLED': app.config['DIRECT_UPLOADS_ENABLED'],
        }

    @app.errorhandler(413)
    def payload_too_large(_error):
        return ('El archivo supera el limite permitido.', 413)

    @app.errorhandler(429)
    def rate_limited(_error):
        return ('Demasiados intentos. Espera un momento e intenta de nuevo.', 429)

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        from app.models import crear_log_audit
        app.logger.warning('csrf_validation_failed reason=%s', error.description)

        log_path = request.path
        if log_path.startswith('/reset-password/'):
            log_path = '/reset-password/[REDACTED]'

        crear_log_audit(
            user_id=session.get('user_id'),
            action='CSRF_FAILURE',
            resource='web',
            details={'reason': error.description, 'path': log_path},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        return ('Tu formulario expiro o no paso la validacion de seguridad.', 400)

    @app.errorhandler(500)
    @app.errorhandler(Exception)
    def handle_internal_server_error(error):
        """Global error handler to log tracebacks securely and present a clean error screen (Fail Securely)."""
        from werkzeug.exceptions import HTTPException
        if isinstance(error, HTTPException):
            return error

        import html
        from flask import jsonify
        app.logger.exception('unhandled_exception_occurred')

        request_id = getattr(g, 'request_id', '-')
        safe_request_id = html.escape(request_id)

        # Determine if JSON is expected by the client
        if request.path.startswith('/api/') or (request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html):
            return jsonify({
                'error': 'Ocurrio un error interno en el servidor.',
                'request_id': safe_request_id
            }), 500

        html_content = (
            f"<!DOCTYPE html>\n"
            f"<html>\n"
            f"<head>\n"
            f"  <meta charset='UTF-8'>\n"
            f"  <title>Error Interno - GameVault</title>\n"
            f"</head>\n"
            f"<body style='font-family: sans-serif; text-align: center; padding: 50px; background: #0f172a; color: #f8fafc;'>\n"
            f"  <h1 style='color: #ef4444;'>Error Interno del Servidor</h1>\n"
            f"  <p>Lo sentimos, ha ocurrido un error inesperado en nuestro sistema.</p>\n"
            f"  <p style='color: #94a3b8;'>ID de solicitud: <strong>{safe_request_id}</strong></p>\n"
            f"  <p><a href='/' style='color: #3b82f6; text-decoration: none;'>Volver al inicio</a></p>\n"
            f"</body>\n"
            f"</html>"
        )
        return (html_content, 500)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        """Releases database connections back to the pool to prevent resource exhaustion (DoS)."""
        from app.models import get_session_factory
        session_factory = get_session_factory()
        if session_factory:
            session_factory.remove()

    from app.models import ensure_bootstrap_admin, init_database
    from app.routes import main_bp

    try:
        init_database()
        if app.config['BOOTSTRAP_ADMIN_ENABLED']:
            ensure_bootstrap_admin(
                email=app.config['BOOTSTRAP_ADMIN_EMAIL'],
                password=app.config['BOOTSTRAP_ADMIN_PASSWORD'],
                nombre=app.config['BOOTSTRAP_ADMIN_NAME'],
                apellido=app.config['BOOTSTRAP_ADMIN_LAST_NAME'],
            )
    except Exception as exc:
        app.logger.warning('database_init_failed_on_startup error=%s', exc)

    app.register_blueprint(main_bp, url_prefix='/')
    return app


app = create_app()
