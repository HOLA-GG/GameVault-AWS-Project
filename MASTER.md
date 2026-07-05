# GameVault - Master Guide

## Vision

GameVault es un SaaS B2C para coleccionistas de videojuegos. La aplicacion web corre en Flask y utiliza una infraestructura moderna basada en Render (Hosting), Neon (PostgreSQL) y Cloudflare R2 (Storage compatible con S3). El objetivo de esta version es dejarla lista para una beta publica profesional con alta escalabilidad y facilidad de despliegue.

## Arquitectura objetivo

```text
Usuario
  |
  v
Render (Flask / Gunicorn / WSGI)
  | \
  |  \__ Resend / SMTP
  |
  +---- Neon (PostgreSQL)
  |
  +---- Cloudflare R2 (Storage S3-compatible)
```

## Componentes

- `wsgi.py`: entrada productiva para PythonAnywhere u otro host WSGI.
- `run.py`: arranque local de desarrollo.
- `app/__init__.py`: configuracion central, logging, Sentry, cookies y extensiones.
- `app/routes.py`: rutas publicas, privadas, admin, perfil y password reset.
- `app/models.py`: acceso a DynamoDB y S3.
- `setup_dynamodb.py`: provision de tablas, TTL e indices.
- `setup_s3.py`: provision de bucket privado, CORS, cifrado y versionado.
- `migrate_password_reset.py`: recreacion de tabla de tokens si hace falta.

## Variables de entorno

Las claves obligatorias en produccion son:

- `APP_ENV=production`
- `SECRET_KEY`
- `DATABASE_URL` (Neon PostgreSQL)
- `MAIL_SERVER`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`

Variables opcionales o de almacenamiento (R2):

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT_URL`
- `SENTRY_DSN`
- `RESET_TOKEN_EXPIRY_MINUTES`
- `AUDIT_LOG_RETENTION_DAYS`
- `RATELIMIT_STORAGE_URI`

Variables Legacy (AWS):

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `DYNAMODB_TABLE`

## Flujos importantes

### Autenticacion

- Registro simple con nombre, email y password.
- Login con rate limiting.
- Logout solo por `POST`.
- Password reset sin revelar si el usuario existe.

### Dashboard

- Requiere sesion.
- Tiene busqueda, filtros, orden y paginacion.
- Las imagenes se cargan a S3 desde el navegador con `presigned POST`.
- Las imagenes se muestran con URL firmada temporal, compatible con bucket privado.

### Admin

- Panel con paginacion de usuarios.
- Logs exportables en CSV.
- Acciones sensibles solo por `POST`.

## Provision inicial

### 1. Dependencias

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Variables

```bash
cp .env.example .env
# Configura las variables en tu entorno local
```

### 3. Base de Datos (Neon)

Neon aprovisiona la base de datos automáticamente al conectar. La aplicación inicializa las tablas en el primer arranque mediante SQLAlchemy.

### 4. Ejecucion local

```bash
python3 run.py
```

### 5. Produccion en Render

Render detecta automáticamente el archivo `render.yaml` o puedes configurar un `Web Service` manual:

- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn wsgi:application --bind 0.0.0.0:$PORT`
- **Environment**: Define las variables de entorno de `.env.example` en el panel de Render.
- **Healthcheck**: Apunta a `/healthz`.

## Modelo de seguridad de esta version

- Secretos solo por entorno.
- `debug` fuera de produccion.
- Cookies seguras y `httponly`.
- CSRF global en formularios.
- Rate limiting en auth y reset.
- S3 privado con CORS restringido.
- TTL para tokens y logs.
- Sentry opcional para errores.

## Riesgos aun abiertos

- `obtener_estadisticas_logs()` sigue usando scan y debe migrarse a agregados dedicados si el volumen crece.
- Falta verificacion de email.
- Falta analitica de conversion.
- Aun no hay backups documentados de negocio ni automatizacion de deploy productivo.
