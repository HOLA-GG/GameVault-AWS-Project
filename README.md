# GameVault

GameVault es una aplicación Flask para coleccionistas de videojuegos. Esta versión ya está preparada para correr con `Render` y `Neon`, con despliegue por `wsgi.py`, panel admin, colecciones públicas y votos de portada por IP.

## Stack

- `Flask` con factory app y entrada `wsgi.py`
- `SQLAlchemy` sobre `PostgreSQL / Neon`
- `Gunicorn` para producción
- `SES SMTP` o proveedor SMTP compatible para emails transaccionales
- `Sentry` opcional para errores

## Lo que ya implementa esta version

- Autenticacion con registro, login, logout y password reset
- Dashboard privado con busqueda, filtros, orden y paginacion
- Perfil de usuario con actualizacion de datos y cambio de password
- Colecciones publicas opcionales para portada
- Valoraciones con estrellas en Inicio, bloqueadas por IP duplicada por colección
- CSRF, rate limiting y cookies endurecidas
- Healthcheck en `/healthz`
- Panel admin con paginacion y export de logs
- WSGI listo para produccion

## Despliegue en Render

1. Crea un `Web Service` conectado a este repo.
2. Usa como `Build Command`:

```bash
pip install -r requirements.txt
```

3. Usa como `Start Command`:

```bash
gunicorn wsgi:application --bind 0.0.0.0:$PORT
```

4. Carga las variables de entorno desde [.env.example](./.env.example).
5. Verifica el despliegue en `/healthz`.

## Variables importantes

Consulta [.env.example](./.env.example) para la lista completa. Las principales para Render son:

- `APP_ENV`
- `SECRET_KEY`
- `DATABASE_URL`
- `STORAGE_BACKEND`
- `MAIL_SERVER`
- `MAIL_USERNAME`
- `MAIL_PASSWORD`
- `MAIL_DEFAULT_SENDER`
- `BOOTSTRAP_ADMIN_EMAIL`
- `BOOTSTRAP_ADMIN_PASSWORD`

## Trabajo local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

Para un paso a paso corto de desarrollo, mira [LOCAL_DEV.md](./LOCAL_DEV.md).

## Tests

```bash
pytest
```

## Siguientes pasos recomendados

- Definir el storage definitivo de imágenes
- Añadir CI/CD con secrets de entorno separados por ambiente
- Conectar un dominio propio y HTTPS estricto
- Añadir analítica de conversión y onboarding guiado
