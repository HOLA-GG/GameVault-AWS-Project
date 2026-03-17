# GameVault

GameVault es una aplicacion Flask para coleccionistas de videojuegos. Corre bien con `PythonAnywhere` como hosting web y mantiene `DynamoDB + S3` en AWS para datos, auditoria e imagenes.

## Stack

- `Flask` con factory app y entrada `wsgi.py`
- `DynamoDB` para usuarios, juegos, tokens y auditoria
- `S3` para portadas con cargas firmadas desde el navegador
- `SES SMTP` para emails transaccionales
- `Sentry` opcional para errores

## Lo que ya implementa esta version

- Autenticacion con registro, login, logout y password reset
- Dashboard privado con busqueda, filtros, orden y paginacion
- Perfil de usuario con actualizacion de datos y cambio de password
- Upload directo a S3 con `presigned POST`
- CSRF, rate limiting y cookies endurecidas
- Healthcheck en `/healthz`
- Panel admin con paginacion y export de logs
- WSGI listo para produccion

## Arranque local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
export $(grep -v '^#' .env | xargs)
python3 run.py
```

## Variables importantes

Consulta [.env.example](./.env.example) para la lista completa. Las mas sensibles son:

- `APP_ENV`
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

## Provision de AWS

```bash
python3 setup_dynamodb.py
python3 setup_s3.py
```

Si necesitas recrear la tabla de tokens:

```bash
python3 migrate_password_reset.py
```

## Despliegue en PythonAnywhere

1. Crea un `virtualenv` e instala `requirements.txt`.
2. Sube el proyecto al home del usuario.
3. Configura las variables de entorno en el archivo WSGI o desde consola.
4. En el archivo WSGI de PythonAnywhere importa `application` desde [`wsgi.py`](/home/juanfune/Documentos/Codigos_De_Visual/Apicacion_Web_AWS/AWS-Computing/wsgi.py).
5. Define `S3_ALLOWED_ORIGINS` con tu dominio final.
6. Recarga la web app y prueba `/healthz`.

## Tests

```bash
pytest
```

## Siguientes pasos recomendados

- Añadir CI/CD con secrets de entorno separados por ambiente
- Conectar un dominio propio y HTTPS estricto
- Añadir analitica de conversion y onboarding guiado
- Sustituir estadisticas scan-based por consultas agregadas dedicadas
