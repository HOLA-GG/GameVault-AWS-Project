# Modo Local de GameVault

Esta guía es la chuleta rápida para volver a levantar el proyecto en desarrollo sin depender del chat.

## 1. Crear y activar el entorno

```bash
cd /home/juanfune/Documentos/Codigos_De_Visual/Apicacion_Web_AWS/AWS-Computing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Variables recomendadas para desarrollo

Usa un `.env` local con este contenido:

```env
APP_ENV=development
SECRET_KEY=local-dev-secret
DATABASE_URL=sqlite+pysqlite:///gamevault_dev.db
STORAGE_BACKEND=local
LOCAL_UPLOAD_DIR=
LOCAL_UPLOAD_URL_PATH=/static/uploads
SHOW_RESET_DEBUG_TOKEN=true
PREFERRED_URL_SCHEME=http
SESSION_COOKIE_SECURE=false
SESSION_COOKIE_HTTPONLY=true
SESSION_COOKIE_SAMESITE=Lax
WTF_CSRF_ENABLED=true
WTF_CSRF_TIME_LIMIT=3600
WTF_CSRF_SSL_STRICT=false
LOG_LEVEL=INFO
SENTRY_DSN=
SENTRY_TRACES_SAMPLE_RATE=0.0
RATELIMIT_STORAGE_URI=memory://
MAX_UPLOAD_MB=5
GAMES_PER_PAGE=12
ADMIN_USERS_PER_PAGE=25
ADMIN_LOGS_PER_PAGE=50
RESET_TOKEN_EXPIRY_MINUTES=30
AUDIT_LOG_RETENTION_DAYS=90
MAIL_SERVER=
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USE_SSL=false
MAIL_USERNAME=
MAIL_PASSWORD=
MAIL_DEFAULT_SENDER=GameVault <noreply@gamevault.app>
MAIL_SUPPRESS_SEND=true
BOOTSTRAP_ADMIN_ENABLED=true
BOOTSTRAP_ADMIN_EMAIL=admin@gamevault
BOOTSTRAP_ADMIN_PASSWORD=12345678
BOOTSTRAP_ADMIN_NAME=GameVault
BOOTSTRAP_ADMIN_LAST_NAME=Admin
```

## 3. Arrancar la app

```bash
cd /home/juanfune/Documentos/Codigos_De_Visual/Apicacion_Web_AWS/AWS-Computing
APP_ENV=development DATABASE_URL=sqlite+pysqlite:///gamevault_dev.db STORAGE_BACKEND=local SHOW_RESET_DEBUG_TOKEN=true MAIL_SUPPRESS_SEND=true SESSION_COOKIE_SECURE=false SECRET_KEY=local-dev-secret FLASK_DEBUG=true FLASK_RUN_HOST=127.0.0.1 FLASK_RUN_PORT=5000 .venv/bin/python run.py
```

La app queda en:

```text
http://127.0.0.1:5000
```

## 4. Detenerla

Si está corriendo en esa misma terminal:

```bash
Ctrl + C
```

Si la dejaste abierta y perdiste la terminal:

```bash
pkill -f "run.py"
```

## 5. Verificación rápida

- `/healthz` debe responder `status: ok`
- `admin@gamevault / 12345678` sirve para entrar al panel admin local
- en desarrollo, el reset password puede mostrar el token si `SHOW_RESET_DEBUG_TOKEN=true`

## 6. Antes de subir a Render

- cambia `APP_ENV` a `production`
- cambia `DATABASE_URL` por la de Neon
- deja `STORAGE_BACKEND=none` si todavía no activaste storage definitivo
- desactiva `SHOW_RESET_DEBUG_TOKEN`
- usa una `SECRET_KEY` larga y nueva
