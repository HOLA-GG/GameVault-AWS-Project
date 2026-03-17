# Migracion a PythonAnywhere + Neon + Cloudflare R2

Guia operativa para preparar la nueva infraestructura de GameVault por tu lado, sin cambiar todavia el codigo interno de la app.

## Objetivo

La arquitectura objetivo queda asi:

- `PythonAnywhere -> Flask -> Neon Postgres`
- `PythonAnywhere -> Flask -> Cloudflare R2`
- `Flask -> Resend`

Importante:

- `PythonAnywhere free` sirve para pruebas y demos temporales.
- `PythonAnywhere free` no es la ruta final para dominio propio ni para una publicacion profesional seria.
- Esta guia es solo para cuentas, paneles, secretos, variables y orden de despliegue.
- La migracion del codigo de `DynamoDB/S3` a `Postgres/R2` sera la fase siguiente.

---

## Tabla de decisiones del stack

| Servicio | Para que se usa | Plan gratis o limitacion principal | Dato que debes copiar al proyecto |
|---|---|---|---|
| `PythonAnywhere` | Hosting de Flask y archivo WSGI | Free: 1 web app, 1 mes de expiracion, recursos limitados, sin dominio propio | `username`, ruta del proyecto, ruta del virtualenv, ruta del WSGI, URL publica temporal |
| `Neon` | Base de datos `Postgres` para usuarios, juegos, logs y tokens | Free disponible; despues escala por uso | `DATABASE_URL`, host, db name, user, password |
| `Cloudflare R2` | Reemplazo de `S3` para imagenes y archivos | Requiere activar R2 y generar credenciales S3-compatible | `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET_NAME`, `R2_ENDPOINT_URL` |
| `Resend` | Emails transaccionales futuros | Free disponible con limites diarios y mensuales | `RESEND_API_KEY`, remitente aprobado, dominio o email remitente |

---

## Antes de tocar el codigo, reune esto

### Variables obligatorias para arrancar una demo futura

- `APP_ENV=production`
- `SECRET_KEY`
- `DATABASE_URL`
- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT_URL`
- `PYTHONANYWHERE_DOMAIN`

### Variables recomendadas para dejar listas desde ya

- `MAIL_DEFAULT_SENDER`
- `RESEND_API_KEY`
- `PYTHONANYWHERE_USERNAME`
- `PYTHONANYWHERE_PROJECT_PATH`
- `PYTHONANYWHERE_VENV_PATH`
- `PYTHONANYWHERE_WSGI_PATH`

### Variables que pueden esperar si aun no activas correo real

- `RESEND_API_KEY`
- `MAIL_DEFAULT_SENDER`

Consejo:

- guarda todo primero en un documento privado o gestor de secretos;
- no pegues credenciales dentro del codigo;
- no las subas al repositorio.

---

## 1. PythonAnywhere

### Que vas a hacer

- Crear la cuenta.
- Crear la web app con configuracion manual.
- Crear el virtualenv.
- Subir el repo.
- Dejar localizada la ruta del WSGI.

### Paso a paso

1. Crea tu cuenta en PythonAnywhere.
2. Entra al panel y ve a `Web`.
3. Haz clic en `Add a new web app`.
4. Elige `Manual configuration`.
5. Elige la version de Python 3 que te ofrezca el panel.
6. Ve a `Consoles` y abre una consola `Bash`.
7. Crea un virtualenv con la misma version de Python que elegiste para la web app.
8. Sube tu repo a tu home de PythonAnywhere.
9. Ubica el proyecto, por ejemplo en una ruta tipo `/home/TU_USUARIO/AWS-Computing`.
10. En `Web`, localiza el archivo `WSGI configuration file`.
11. Todavia no conectes dominio propio; en free usaras un subdominio temporal de PythonAnywhere.

### Que debes anotar

- `username`
- ruta completa del proyecto
- ruta completa del virtualenv
- ruta completa del archivo WSGI
- URL publica temporal tipo `tuusuario.pythonanywhere.com`

### Nota importante

PythonAnywhere documenta que Flask en produccion debe cargarse desde el archivo WSGI, no desde `app.run()`. Tu proyecto ya tiene [`wsgi.py`](/home/juanfune/Documentos/Codigos_De_Visual/Apicacion_Web_AWS/AWS-Computing/wsgi.py), asi que eso va en la direccion correcta.

### Dato final que debes copiar

- `PYTHONANYWHERE_DOMAIN`
- `PYTHONANYWHERE_USERNAME`
- `PYTHONANYWHERE_PROJECT_PATH`
- `PYTHONANYWHERE_VENV_PATH`
- `PYTHONANYWHERE_WSGI_PATH`

---

## 2. Neon

### Que vas a hacer

- Crear la cuenta.
- Crear un proyecto.
- Crear o usar la base de datos Postgres del proyecto.
- Copiar la cadena de conexion.

### Paso a paso

1. Crea tu cuenta en Neon.
2. Crea un proyecto nuevo para GameVault.
3. Elige la region mas cercana a tus usuarios o a tu hosting.
   Mi recomendacion para tu caso: elegir una region cercana a Americas.
4. Entra al dashboard del proyecto.
5. Pulsa `Connect`.
6. En la ventana de conexion, selecciona:
   - branch,
   - database,
   - role.
7. Copia la connection string completa.
8. Guarda tambien por separado host, nombre de base, usuario y password.

### Que debes obtener

- `DATABASE_URL`
- host
- `db name`
- `user`
- `password`
- `sslmode`

### Nota de seguridad

- guarda la connection string completa en un lugar privado;
- no la pegues en el codigo;
- usala luego como variable de entorno `DATABASE_URL`;
- Neon trabaja como un Postgres normal, asi que esa cadena sera la base de la futura migracion.

### Dato final que debes copiar

- `DATABASE_URL`
- `NEON_HOST`
- `NEON_DB_NAME`
- `NEON_USER`
- `NEON_PASSWORD`
- `NEON_SSLMODE`

---

## 3. Cloudflare R2

### Que vas a hacer

- Crear cuenta en Cloudflare.
- Activar `R2`.
- Crear un bucket.
- Generar credenciales compatibles con S3.

### Paso a paso

1. Crea tu cuenta en Cloudflare.
2. Entra al dashboard.
3. Ve a `Storage & databases > R2`.
4. Activa R2 si es la primera vez.
5. Crea un bucket nuevo para GameVault.
   Ejemplo de nombre: `gamevault-media`
6. Ve a `Manage API Tokens`.
7. Crea un token nuevo.
8. Elige permisos `Object Read & Write`.
9. Si el panel lo permite, limita el token solo al bucket que acabas de crear.
10. Crea el token.
11. Copia inmediatamente:
    - `Access Key ID`
    - `Secret Access Key`
12. Copia tambien:
    - `Account ID`
    - endpoint S3-compatible

### Que debes obtener

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT_URL`

### Nota importante

R2 reemplaza a S3 con muy poco trauma porque ofrece API compatible con S3. Eso significa que esta parte de la migracion deberia ser mucho mas simple que el cambio de DynamoDB a Postgres.

### Dato final que debes copiar

- `R2_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`
- `R2_BUCKET_NAME`
- `R2_ENDPOINT_URL`

---

## 4. Resend

### Que vas a hacer

- Crear la cuenta.
- Verificar dominio o preparar el remitente.
- Crear API key.

### Paso a paso

1. Crea tu cuenta en Resend.
2. Si ya tienes dominio propio, agregalo y verifica sus DNS.
3. Si aun no tienes dominio propio, deja esta parte preparada para mas adelante.
4. Ve a `API Keys`.
5. Crea una API key nueva.
6. Si puedes, usa una key de envio y no una full access para produccion futura.
7. Guarda la key inmediatamente.
8. Define el remitente que mas adelante usaras en la app.
   Ejemplo: `GameVault <noreply@tudominio.com>`

### Que debes obtener

- `RESEND_API_KEY`
- remitente aprobado
- dominio verificado o email remitente futuro

### Nota importante

En Resend no necesitas “crear” manualmente una direccion remitente si ya verificaste el dominio; puedes enviar desde una direccion de ese dominio. Para la demo, si aun no activas correo real, esta parte puede quedarse pendiente.

### Dato final que debes copiar

- `RESEND_API_KEY`
- `MAIL_DEFAULT_SENDER`

---

## 5. Plantilla de datos a guardar

Usa esta lista como inventario privado:

```env
APP_ENV=production
SECRET_KEY=

PYTHONANYWHERE_DOMAIN=
PYTHONANYWHERE_USERNAME=
PYTHONANYWHERE_PROJECT_PATH=
PYTHONANYWHERE_VENV_PATH=
PYTHONANYWHERE_WSGI_PATH=

DATABASE_URL=
NEON_HOST=
NEON_DB_NAME=
NEON_USER=
NEON_PASSWORD=
NEON_SSLMODE=require

R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=
R2_ENDPOINT_URL=

RESEND_API_KEY=
MAIL_DEFAULT_SENDER=
```

---

## 6. Orden exacto de ejecucion

Sigue este orden y no te saltes pasos:

1. Crear cuenta en `PythonAnywhere`.
2. Crear cuenta y proyecto en `Neon`.
3. Crear cuenta y bucket en `Cloudflare R2`.
4. Crear cuenta en `Resend` o dejarla pendiente si aun no activas correo.
5. Reunir todos los secretos y endpoints.
6. Preparar un `.env` local nuevo orientado a `Neon + R2`.
7. Subir el proyecto a `PythonAnywhere`.
8. Crear virtualenv e instalar dependencias.
9. Configurar variables en el WSGI o entorno del hosting.
10. Confirmar que la app responde con `/healthz`.
11. Dejar explicitamente pendiente la migracion interna del codigo de `DynamoDB/S3` hacia `Postgres/R2`.

---

## 7. Que si y que no tendras gratis

### Si tendras

- una ruta realista para prototipar y aprender el despliegue;
- una URL publica temporal;
- una base Postgres moderna;
- un storage compatible con S3;
- una plataforma de correo lista para cuando toque activarla.

### No tendras todavia

- dominio propio serio desde `PythonAnywhere free`;
- una publicacion final profesional sin limites;
- la migracion del codigo ya hecha;
- correo productivo completo si pospones `Resend`;
- garantias de capacidad para crecimiento real con el plan free del hosting.

### Traduccion practica

- para demo: esta ruta sirve;
- para salir “de verdad”: tendras que subir al menos el hosting a plan de pago cuando quieras publicar en serio.

---

## 8. Despues de crear las cuentas

Cuando termines esta guia, la siguiente fase tecnica sera:

- migrar `DynamoDB -> Postgres`
- migrar `S3 -> R2`
- sustituir `SES/Flask-Mail` por integracion con `Resend`

Eso ya no es infraestructura externa solamente. Ese paso implica cambiar el codigo de la aplicacion, especialmente:

- la capa de datos,
- las variables de entorno,
- la subida de imagenes,
- y el envio de correos.

---

## 9. Checklist final rapido

- [ ] Tengo cuenta en PythonAnywhere
- [ ] Tengo cuenta en Neon
- [ ] Tengo cuenta en Cloudflare
- [ ] Tengo bucket en R2
- [ ] Tengo credenciales S3-compatible de R2
- [ ] Tengo `DATABASE_URL` de Neon
- [ ] Tengo `SECRET_KEY`
- [ ] Tengo definida la URL temporal de PythonAnywhere
- [ ] Decidi si `Resend` queda listo ahora o despues
- [ ] Ya se que la siguiente fase sera migrar el codigo, no solo subir variables

---

## Fuentes oficiales revisadas

- PythonAnywhere Flask: https://help.pythonanywhere.com/pages/Flask
- PythonAnywhere virtualenvs: https://help.pythonanywhere.com/pages/VirtualEnvForWebsites/
- PythonAnywhere free accounts: https://help.pythonanywhere.com/pages/FreeAccountsFeatures/
- PythonAnywhere custom domains: https://help.pythonanywhere.com/pages/CustomDomains/
- Neon conectar tu app: https://neon.com/docs/get-started/connect-neon
- Neon pricing: https://neon.com/pricing
- Cloudflare R2 S3 API: https://developers.cloudflare.com/r2/get-started/s3/
- Cloudflare R2 auth tokens: https://developers.cloudflare.com/r2/api/s3/tokens
- Resend API keys: https://resend.com/docs/dashboard/api-keys/introduction
- Resend SMTP: https://resend.com/docs/send-with-smtp
- Resend sender/domain: https://resend.com/docs/knowledge-base/how-do-I-create-an-email-address-or-sender-in-resend
- Resend pricing: https://resend.com/pricing
