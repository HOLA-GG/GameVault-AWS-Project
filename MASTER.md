# GameVault - Master Guide

## Vision

GameVault es un SaaS B2C para coleccionistas de videojuegos. La aplicacion web corre en Flask y usa AWS para persistencia, imagenes, correos y auditoria. El objetivo de esta version es dejarla lista para una beta publica profesional sin seguir dependiendo de EC2.

## Arquitectura objetivo

```text
Usuario
  |
  v
PythonAnywhere (Flask / WSGI)
  | \
  |  \__ SES SMTP
  |
  +---- DynamoDB
  |
  +---- S3 (uploads firmados + lectura temporal)
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
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `DYNAMODB_TABLE`
- `DYNAMODB_USERS_TABLE`
- `DYNAMODB_RESET_TABLE`
- `DYNAMODB_AUDIT_TABLE`
- `MAIL_SERVER`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`

Variables recomendadas:

- `SENTRY_DSN`
- `S3_ALLOWED_ORIGINS`
- `RESET_TOKEN_EXPIRY_MINUTES`
- `AUDIT_LOG_RETENTION_DAYS`
- `RATELIMIT_STORAGE_URI`

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
export $(grep -v '^#' .env | xargs)
```

### 3. Infraestructura AWS

```bash
python3 setup_dynamodb.py
python3 setup_s3.py
```

### 4. Ejecucion local

```bash
python3 run.py
```

### 5. Produccion en PythonAnywhere

```python
from wsgi import application
```

En el panel de PythonAnywhere:

- configura el virtualenv,
- define las variables de entorno,
- apunta al proyecto,
- recarga la web app,
- prueba `https://tu-dominio/healthz`.

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
