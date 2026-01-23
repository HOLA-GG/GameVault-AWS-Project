# 🎮 GameVault - Documentación Completa

Aplicación web multi-tenant construida con Flask, Amazon DynamoDB y Amazon S3 para gestionar colecciones de videojuegos en la nube.

---

## 📋 Tabla de Contenidos

1. [Descripción General](#descripción-general)
2. [Arquitectura](#arquitectura)
3. [Características](#características)
4. [Estructura del Proyecto](#estructura-del-proyecto)
5. [Configuración Inicial](#configuración-inicial)
6. [Despliegue en AWS EC2](#despliegue-en-aws-ec2)
7. [Configuración de DynamoDB](#configuración-de-dynamodb)
8. [Configuración de S3](#configuración-de-s3)
9. [Guía de Uso](#guía-de-uso)
10. [Variables de Entorno](#variables-de-entorno)
11. [Ideas para Mejoras Futuras](#ideas-para-mejoras-futuras)
12. [Solución de Problemas](#solución-de-problemas)

---

## 📝 Descripción General

GameVault es una aplicación SaaS que permite a los usuarios gestionar sus colecciones de videojuegos de forma segura en la nube. Cada usuario tiene su propio espacio aislado (multi-tenancy) donde puede agregar, editar y eliminar juegos con sus imágenes almacenadas en S3.

### Público Objetivo
- Coleccionistas de videojuegos que desean digitalizar su colección
- Jugadores casuales que quieren mantener registro de sus juegos
- Tiendas de videojuegos que necesitan gestión de inventario

### Problema que Resuelve
- Almacenamiento centralizado de información de juegos
- Acceso desde cualquier dispositivo
- Organización por plataforma, estado, género
- Copia de seguridad automática en la nube

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS CLOUD                            │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                   EC2 Instance                      │    │
│  │   ┌─────────────────────────────────────────────┐   │    │
│  │   │         Flask Application (GameVault)       │   │    │
│  │   │  ┌─────────┐  ┌─────────┐  ┌─────────────┐  │   │    │
│  │   │  │ Routes  │  │ Models  │  │ Templates   │  │   │    │
│  │   │  └─────────┘  └─────────┘  └─────────────┘  │   │    │
│  │   └─────────────────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────┘    │
│           │                    │                    │       │
│           ▼                    ▼                    ▼       │
│  ┌──────────────┐    ┌─────────────────┐   ┌───────────┐    │
│  │   DynamoDB   │    │       S3        │   │  systemd  │    │
│  │  (Database)  │    │  (Storage)      │   │ (Service) │    │
│  └──────────────┘    └─────────────────┘   └───────────┘    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
        │
        │ HTTPS
        ▼
┌─────────────────────────────────────────────────────────────┐
│                      User Browser                           │
└─────────────────────────────────────────────────────────────┘
```

### Componentes de AWS

| Componente | Función | Tipo |
|------------|---------|------|
| **EC2** | Servidor web hosting Flask | Compute |
| **DynamoDB** | Base de datos NoSQL para juegos y usuarios | Database |
| **S3** | Almacenamiento de imágenes de portadas | Storage |
| **IAM** | Control de permisos y acceso | Security |

### Patrones de Diseño

1. **Multi-Tenancy**: Aislamiento de datos por `user_id`
2. **Factory Pattern**: Application Factory en `__init__.py`
3. **Repository Pattern**: Capa de datos en `models.py`
4. **RESTful Routes**: Endpoints claros y predecibles

---

## ✨ Características

### ✅ Implementadas

| Característica | Descripción |
|----------------|-------------|
| **Gestión de Juegos** | CRUD completo (Crear, Leer, Actualizar, Eliminar) |
| **Imágenes en S3** | Subida automática de portadas a Amazon S3 |
| **Multi-Tenancy** | Cada usuario vé solo sus propios juegos |
| **Autenticación** | Registro, login, logout con sesiones |
| **Recuperación de Contraseña** | Tokens seguros con expiración |
| **Audit Logs** | Registro de todas las acciones |
| **Panel de Admin** | Gestión de usuarios con rol 'admin' |
| **Demo In-Memory** | Prueba sin configurar base de datos |
| **Diseño Responsive** | Tema oscuro adaptable a móviles |
| **Previsualización** | Preview de imágenes antes de subir |

### 🔄 Próximas Características

| Característica | Prioridad | Estimación |
|----------------|-----------|------------|
| API REST completa | Alta | 1 semana |
| JWT Authentication | Alta | 2-3 días |
| Dark/Light Mode | Media | 1 día |
| Búsqueda y Filtros | Media | 2-3 días |
| Integración IGDB | Baja | 2 semanas |
| Sistema de Logros | Baja | 1 semana |
| Pagos con Stripe | Baja | 2 semanas |

---

## 📁 Estructura del Proyecto

```
AWS-Computing/
├── run.py                      # Punto de entrada de la aplicación
├── requirements.txt            # Dependencias Python
├── gamevault.service           # Servicio systemd para EC2
├── setup_dynamodb.py           # Script de configuración DynamoDB
├── setup_s3.py                 # Script de configuración S3
├── migrate_password_reset.py   # Migración de tokens
├── MASTER.md                   # Este archivo
│
├── app/                        # Aplicación principal
│   ├── __init__.py             # Application Factory
│   ├── routes.py               # Controladores y rutas
│   ├── models.py               # Capa de datos (DynamoDB + S3)
│   │
│   ├── static/
│   │   └── css/
│   │       └── styles.css      # Estilos del tema gaming
│   │
│   └── templates/              # Vistas HTML
│       ├── base.html           # Template base
│       ├── landing.html        # Landing page
│       ├── index.html          # Dashboard principal
│       ├── demo_form.html      # Demo in-memory
│       ├── demo_result.html    # Resultado demo
│       ├── login.html          # Inicio de sesión
│       ├── registro.html       # Registro de usuario
│       ├── forgot_password.html    # Recuperar contraseña
│       ├── reset_password.html     # Nueva contraseña
│       ├── validate_token.html     # Validar token
│       ├── admin.html          # Panel de admin
│       ├── admin_logs.html     # Logs de auditoría
│       └── edit_game.html      # Editar juego
```

### Descripción de Archivos Clave

| Archivo | Propósito |
|---------|-----------|
| `run.py` | Ejecuta la aplicación Flask en el puerto 5000 |
| `app/__init__.py` | Inicializa Flask con configuración AWS |
| `app/routes.py` | Define todas las URLs y controladores |
| `app/models.py` | Operaciones CRUD con DynamoDB y S3 |
| `gamevault.service` | Configuración para ejecutar como servicio en EC2 |

---

## ⚙️ Configuración Inicial

### Requisitos Previos

```bash
# Python 3.8 o superior
python3 --version

# AWS CLI configurado (para scripts de setup)
aws configure

# Credenciales AWS con permisos:
# - dynamodb:*
# - s3:*
```

### Instalación de Dependencias

```bash
# Clonar o entrar al directorio del proyecto
cd /home/ec2-user/AWS-Computing

# Crear entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# o: venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt
```

### Dependencias (`requirements.txt`)

```
flask                    # Framework web
flask-mail              # Envío de emails
boto3                   # SDK de AWS para Python
botocore               # Dependencia de boto3
werkzeug               # Seguridad y utilidades
```

---

## 🚀 Despliegue en AWS EC2

### Paso 1: Lanzar Instancia EC2

1. Ir a AWS Console → EC2 → Launch Instance
2. Seleccionar **Amazon Linux 2** o **Ubuntu 22.04**
3. Tipo: **t3.medium** (recomendado) o t2.micro (free tier)
4. Security Group: Abrir puerto 5000 (temporal) y 80/443
5. Asignar IAM Role con permisos DynamoDB y S3

### Paso 2: Conectar a EC2

```bash
# Desde tu máquina local
ssh -i /path/to/your-key.pem ec2-user@<TU-EC2-IP>
```

### Paso 3: Subir Archivos al Servidor

```bash
# Opción 1: SCP (recomendado)
scp -r -i /path/to/your-key.pem /path/to/AWS-Computing ec2-user@<TU-EC2-IP>:/home/ec2-user/

# Opción 2: Git (si el proyecto está en GitHub)
git clone https://github.com/tu-usuario/AWS-Computing.git
```

### Paso 4: Instalar Dependencias en EC2

```bash
# Actualizar sistema
sudo yum update -y  # Amazon Linux
# o: sudo apt update && sudo apt upgrade -y  # Ubuntu

# Instalar Python si no está
sudo yum install python3 python3-pip -y

# Crear entorno virtual
cd /home/ec2-user/AWS-Computing
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### Paso 5: Configurar Servicio Systemd

```bash
# Copiar archivo de servicio
sudo cp /home/ec2-user/AWS-Computing/gamevault.service /etc/systemd/system/

# Recargar systemd
sudo systemctl daemon-reload

# Habilitar servicio (inicio automático)
sudo systemctl enable gamevault.service

# Iniciar servicio
sudo systemctl start gamevault

# Verificar estado
sudo systemctl status gamevault
```

### Paso 6: Verificar que Funciona

```bash
# Ver logs en tiempo real
sudo journalctl -u gamevault -f

# Verificar servicio
sudo systemctl is-active gamevault
```

### Comandos de Gestión

```bash
# Recargar después de cambios
sudo systemctl daemon-reload
sudo systemctl restart gamevault

# Ver estado detallado
sudo systemctl status gamevault

# Ver logs
sudo journalctl -u gamevault              # Todos los logs
sudo journalctl -u gamevault -f           # Logs en tiempo real
sudo journalctl -u gamevault --since "1 hour ago"  # Última hora
```

### Configuración de Proxy Reverso (Opcional pero Recomendado)

```bash
# Instalar Nginx
sudo yum install nginx -y  # Amazon Linux
# o: sudo apt install nginx -y  # Ubuntu

# Crear configuración
sudo nano /etc/nginx/conf.d/gamevault.conf
```

```nginx
server {
    listen 80;
    server_name tu-dominio.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Habilitar y reiniciar Nginx
sudo systemctl enable nginx
sudo systemctl start nginx
sudo systemctl restart nginx
```

---

## 🗄️ Configuración de DynamoDB

### Tablas Requeridas

| Tabla | Partition Key | Sort Key | Descripción |
|-------|---------------|----------|-------------|
| `GameVault` | `user_id` | `game_id` | Almacena los juegos de cada usuario |
| `GameVaultUsers` | `user_id` | - | Almacena datos de usuarios y autenticación |
| `GameVaultPasswordReset` | `token_id` | - | Tokens de recuperación de contraseña |
| `GameVaultAuditLogs` | `audit_id` | - | Logs de auditoría |

### Método 1: Script Automático (Recomendado)

```bash
python setup_dynamodb.py
```

**Salida esperada:**
```
🚀 Configurando DynamoDB para GameVault...
📍 Región: us-east-1
✅ Tabla 'GameVault' ya existe
✅ Tabla 'GameVaultUsers' ya existe
✅ Tabla 'GameVaultPasswordReset' creada exitosamente!
✅ Tabla 'GameVaultAuditLogs' creada exitosamente!
👤 Configurando usuario administrador...
✅ Admin creado exitosamente: admin@gamevault.com
   Password: admin123
🎉 Configuración de DynamoDB completada!
```

### Método 2: AWS CLI Manual

#### Tabla GameVault (Juegos)

```bash
aws dynamodb create-table \
    --table-name GameVault \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=game_id,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
        AttributeName=game_id,KeyType=RANGE \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1
```

#### Tabla GameVaultUsers (Usuarios)

```bash
aws dynamodb create-table \
    --table-name GameVaultUsers \
    --attribute-definitions \
        AttributeName=user_id,AttributeType=S \
        AttributeName=email,AttributeType=S \
    --key-schema \
        AttributeName=user_id,KeyType=HASH \
    --global-secondary-indexes \
        "IndexName=email-index,KeySchema=[{AttributeName=email,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1
```

#### Tabla GameVaultPasswordReset (Tokens)

```bash
aws dynamodb create-table \
    --table-name GameVaultPasswordReset \
    --attribute-definitions \
        AttributeName=token_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
    --key-schema \
        AttributeName=token_id,KeyType=HASH \
    --global-secondary-indexes \
        "IndexName=user_id-index,KeySchema=[{AttributeName=user_id,KeyType=HASH}],Projection={ProjectionType=ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1
```

#### Tabla GameVaultAuditLogs (Auditoría)

```bash
aws dynamodb create-table \
    --table-name GameVaultAuditLogs \
    --attribute-definitions \
        AttributeName=audit_id,AttributeType=S \
        AttributeName=user_id,AttributeType=S \
        AttributeName=timestamp,AttributeType=S \
    --key-schema \
        AttributeName=audit_id,KeyType=HASH \
    --global-secondary-indexes \
        "IndexName=user-timestamp-index,KeySchema=[{AttributeName=user_id,KeyType=HASH},{AttributeName=timestamp,KeyType=RANGE}],Projection={ProjectionType:ALL},ProvisionedThroughput={ReadCapacityUnits=5,WriteCapacityUnits=5}" \
    --provisioned-throughput \
        ReadCapacityUnits=5,WriteCapacityUnits=5 \
    --region us-east-1
```

### Verificación

```bash
# Listar todas las tablas
aws dynamodb list-tables --region us-east-1

# Describir tabla específica
aws dynamodb describe-table --table-name GameVault --region us-east-1

# Insertar dato de prueba
aws dynamodb put-item \
    --table-name GameVault \
    --item '{
        "user_id": {"S": "user-demo-001"},
        "game_id": {"S": "game-001"},
        "titulo": {"S": "Super Mario Bros"},
        "descripcion": {"S": "Juego clásico de Nintendo"},
        "imagen_url": {"S": "https://gamevault-media-files.s3.us-east-1.amazonaws.com/mario.jpg"},
        "plataforma": {"S": "Nintendo"},
        "estado": {"S": "Como Nuevo"}
    }' \
    --region us-east-1
```

---

## 🪣 Configuración de S3

### Bucket Requerido

| Configuración | Valor |
|---------------|-------|
| **Nombre** | `gamevault-media-files` |
| **Región** | `us-east-1` |
| **Acceso** | Público (lectura) |
| **CORS** | Habilitado |
| **Versioning** | Habilitado |

### Script Automático

```bash
python setup_s3.py
```

**Salida esperada:**
```
🚀 Configurando S3 para GameVault...
📍 Bucket: gamevault-media-files
📍 Región: us-east-1
✅ Bucket 'gamevault-media-files' ya existe
✅ Block Public Access configurado correctamente
✅ Política del bucket configurada (lectura pública)
✅ CORS configurado correctamente
✅ Versioning habilitado correctamente
📍 Región del bucket: us-east-1
✅ Bucket verificado exitosamente
🎉 Configuración de S3 completada!
```

### Crear Bucket Manualmente

```bash
# Crear bucket
aws s3 mb s3://gamevault-media-files --region us-east-1

# Desactivar block public access
aws s3api put-public-access-block \
    --bucket gamevault-media-files \
    --public-access-block-configuration \
        "BlockPublicAcls=false,IgnorePublicAcls=false,BlockPublicPolicy=false,RestrictPublicBuckets=false"

# Configurar política de lectura pública
aws s3api put-bucket-policy \
    --bucket gamevault-media-files \
    --policy '{
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": "arn:aws:s3:::gamevault-media-files/*"
            }
        ]
    }'

# Configurar CORS
aws s3api put-bucket-cors \
    --bucket gamevault-media-files \
    --cors-configuration '{
        "CORSRules": [
            {
                "AllowedHeaders": ["*"],
                "AllowedMethods": ["GET", "PUT", "POST", "DELETE", "HEAD"],
                "AllowedOrigins": ["*"],
                "ExposeHeaders": ["ETag"],
                "MaxAgeSeconds": 3000
            }
        ]
    }'

# Habilitar versioning
aws s3api put-bucket-versioning \
    --bucket gamevault-media-files \
    --versioning-configuration 'Status=Enabled'
```

### Verificación

```bash
# Verificar bucket
aws s3 ls s3://gamevault-media-files

# Probar acceso público
aws s3 cp s3://gamevault-media-files/test.txt /tmp/test.txt

# Ver política
aws s3api get-bucket-policy --bucket gamevault-media-files
```

---

## 📖 Guía de Uso

### Acceso a la Aplicación

| Entorno | URL | Puerto |
|---------|-----|--------|
| **Local** | http://localhost:5000 | 5000 |
| **EC2 Directo** | http://<EC2-IP>:5000 | 5000 |
| **Con Nginx** | http://tu-dominio.com | 80 |

### Rutas Disponibles

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Landing Page |
| `/demo` | GET/POST | Demo in-memory (sin BD) |
| `/dashboard` | GET | Panel principal |
| `/agregar` | POST | Agregar juego |
| `/delete/<game_id>` | GET | Eliminar juego |
| `/edit/<game_id>` | GET/POST | Editar juego |
| `/registro` | GET/POST | Registrarse |
| `/login` | GET/POST | Iniciar sesión |
| `/logout` | GET | Cerrar sesión |
| `/forgot-password` | GET/POST | Recuperar contraseña |
| `/reset-password/<token>` | GET/POST | Nueva contraseña |
| `/admin` | GET | Panel de administración |
| `/admin/logs` | GET | Logs de auditoría |
| `/salud` | GET | Health check |

### Usuario Administrador

Por defecto, se crea un usuario administrador:

| Campo | Valor |
|-------|-------|
| **Email** | admin@gamevault.com |
| **Password** | admin123 |

### Demo In-Memory

La ruta `/demo` permite probar la aplicación sin configurar DynamoDB:

1. Ir a `/demo`
2. Llenar formulario con título e imagen
3. La imagen se procesa en memoria (no se sube a S3)
4. Ver resultado inmediato

---

## 🔐 Variables de Entorno

### Configuración Recomendada

```bash
# Aplicación
export FLASK_APP=run.py
export FLASK_ENV=production
export SECRET_KEY='tu-secret-key-muy-largo-y-aleatorio'

# AWS (si no usas IAM Role)
export AWS_ACCESS_KEY_ID=tu_access_key
export AWS_SECRET_ACCESS_KEY=tu_secret_key
export AWS_REGION=us-east-1

# DynamoDB
export DYNAMODB_TABLE=GameVault
export DYNAMODB_USERS_TABLE=GameVaultUsers
export DYNAMODB_RESET_TABLE=GameVaultPasswordReset
export DYNAMODB_AUDIT_TABLE=GameVaultAuditLogs

# S3
export S3_BUCKET_NAME=gamevault-media-files
export S3_REGION=us-east-1

# Email (para recuperación de contraseña)
export MAIL_SERVER=smtp.gmail.com
export MAIL_PORT=587
export MAIL_USE_TLS=true
export MAIL_USERNAME=tu_email@gmail.com
export MAIL_PASSWORD=tu_app_password
export MAIL_DEFAULT_SENDER='GameVault <noreply@gamevault.com>'

# Recuperación de contraseña
export RESET_TOKEN_EXPIRY_MINUTES=60

# Retención de logs
export AUDIT_LOG_RETENTION_DAYS=90
```

### En el Servicio Systemd

Edita `/etc/systemd/system/gamevault.service`:

```ini
[Service]
Environment=FLASK_ENV=production
Environment=SECRET_KEY=tu-secret-key-aqui
Environment=AWS_REGION=us-east-1
Environment=DYNAMODB_TABLE=GameVault
Environment=DYNAMODB_USERS_TABLE=GameVaultUsers
Environment=S3_BUCKET_NAME=gamevault-media-files
# ... más variables
```

---

## 💡 Ideas para Mejoras Futuras

### 🔐 Seguridad Avanzada

#### Autenticación JWT
```python
from flask_jwt_extended import JWTManager, create_access_token

@app.route('/api/login', methods=['POST'])
def api_login():
    access_token = create_access_token(identity=user_id, expires_delta=timedelta(hours=24))
    return jsonify(access_token=access_token)
```

#### Two-Factor Authentication (2FA)
- Integración con Google Authenticator (TOTP)
- Envío de códigos por SMS (Twilio)
- Códigos de backup de emergencia

#### Rate Limiting
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(app, key_func=get_remote_address)
limiter.limit("50 per hour")
```

---

### 💳 Sistema de Suscripciones

| Plan | Precio | Storage | API Calls |
|------|--------|---------|-----------|
| **Free** | $0 | 100 MB | 1,000/mes |
| **Pro** | $9.99/mes | 5 GB | 10,000/mes |
| **Enterprise** | $29.99/mes | 50 GB | 100,000/mes |

#### Integración con Stripe
```python
import stripe

stripe.api_key = 'sk_test_...'

# Crear cliente
customer = stripe.Customer.create(email=user_email)

# Crear suscripción
subscription = stripe.Subscription.create(
    customer=customer.id,
    items=[{'price': 'price_PRO_id'}]
)
```

---

### 📊 Analytics y Dashboard

#### Métricas a Mostrar
- Total de juegos por usuario
- Storage usado vs disponible
- Juegos subidos este mes
- Actividad de los últimos 7 días
- Distribución por plataforma

#### Gráficos Recomendados
- Chart.js para gráficos de barras y líneas
- Recharts para dashboards interactivos
- D3.js para visualizaciones avanzadas

---

### 🤖 Inteligencia Artificial

#### Clasificación de Imágenes (AWS Rekognition)
```python
import boto3

def clasificar_imagen(imagen_url):
    client = boto3.client('rekognition')
    response = client.detect_labels(
        Image={'S3Object': {'Bucket': bucket, 'Name': key}},
        MaxLabels=10, MinConfidence=75
    )
    return [label['Name'] for label in response['Labels']]
```

#### Recomendaciones Personalizadas
- Basado en géneros de juegos guardados
- Similitud con otros usuarios
- Tendencias populares

#### Detección de Duplicados
- Hash de imágenes para detectar duplicados
- Similitud en títulos (fuzzy matching)
- Alerta antes de subir duplicado

---

### 🔗 Integraciones Externas

#### IGDB API (Internet Game Database)
```python
IGDB_ENDPOINT = "https://api.igdb.com/v4/games"
headers = {
    'Client-ID': client_id,
    'Authorization': f'Bearer {access_token}'
}
```

#### Steam API Integration
```python
STEAM_API = "http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
```

#### OAuth Login
```python
from authlib.integrations.flask_client import OAuth

oauth.register(
    name='google',
    client_id='...',
    client_secret='...',
    access_token_url='...',
    authorize_url='...'
)
```

---

### 📱 Experiencia de Usuario

#### PWA Support
```json
{
    "name": "GameVault",
    "short_name": "GameVault",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#1a1a2e",
    "theme_color": "#6c5ce7"
}
```

#### Drag & Drop Upload
```javascript
dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    const files = e.dataTransfer.files;
    uploadFiles(files);
});
```

#### Operaciones en Masa
```python
@main_bp.route('/bulk-delete', methods=['POST'])
def bulk_delete():
    game_ids = request.json.get('game_ids', [])
    for game_id in game_ids:
        eliminar_juego(user_id, game_id)
    return jsonify(success=True, deleted=len(game_ids))
```

---

### 🏢 Sistema Multi-Tenant Avanzado

#### Custom Branding
```python
TENANT_CONFIG = {
    'logo_url': 'https://...',
    'primary_color': '#6c5ce7',
    'company_name': 'Mi Tienda',
    'custom_domain': 'juegos.miempresa.com'
}
```

#### Team Members
| Rol | Permisos |
|-----|----------|
| **Owner** | Todo + facturación |
| **Admin** | Gestionar usuarios |
| **Editor** | Crear/editar contenido |
| **Viewer** | Solo lectura |

---

### 🎮 Gamification

#### Sistema de Logros
```python
ACHIEVEMENTS = {
    'first_game': {'name': 'Iniciado', 'points': 10},
    'collector_10': {'name': 'Coleccionista', 'points': 50},
    'collector_100': {'name': 'Maestro', 'points': 500}
}
```

#### Niveles
| Nivel | Puntos | Badge |
|-------|--------|-------|
| Novato | 0 | 🌱 |
| Jugador | 100 | 🎮 |
| Coleccionista | 500 | 📚 |
| Experto | 1,000 | ⭐ |
| Maestro | 5,000 | 👑 |

---

## 🐛 Solución de Problemas

### El servicio no inicia

```bash
# Verificar errores
sudo journalctl -u gamevault -p err

# Verificar sintaxis del archivo de servicio
sudo systemd-analyze verify /etc/systemd/system/gamevault.service

# Verificar que el puerto 5000 está disponible
sudo netstat -tulpn | grep 5000
```

### Error de DynamoDB

```bash
# Verificar región
aws configure get region

# Verificar credenciales
aws sts get-caller-identity

# Tabla ya existe
aws dynamodb delete-table --table-name GameVault --region us-east-1
```

### Error de S3

```bash
# Bucket no existe
aws s3 mb s3://gamevault-media-files

# Permisos denegados
aws s3api put-bucket-policy --bucket gamevault-media-files --policy file://policy.json
```

### CSS no se aplica

1. Verificar que `static/css/styles.css` existe
2. Verificar que el template usa `{{ url_for('static', filename='css/styles.css') }}`
3. Verificar permisos de archivos:
   ```bash
   chmod 755 app/static/css/styles.css
   ```

### Imágenes no se suben

1. Verificar que el bucket existe
2. Verificar que CORS está configurado
3. Verificar política de acceso público
4. Revisar logs:
   ```bash
   sudo journalctl -u gamevault -f
   ```

---

## 📊 Estimación de Costos AWS

### Plan Free Tier

| Servicio | Uso | Costo |
|----------|-----|-------|
| EC2 | t2.micro (750 hrs/mes) | $0 |
| DynamoDB | 25 GB almacenamiento | $0 |
| S3 | 100 MB almacenamiento | $0 |
| **Total** | | **$0/mes** |

### Plan Pro (500 usuarios)

| Servicio | Uso | Costo Aproximado |
|----------|-----|------------------|
| EC2 | t3.medium | $25/mes |
| DynamoDB | 5 GB + RCU/WCU | $15/mes |
| S3 | 5 GB + requests | $2/mes |
| **Total** | | **$42/mes** |

---

## 🚀 Despliegue en Producción

### Checklist Pre-Despliegue

- [ ] Cambiar `debug=True` a `False` en `run.py`
- [ ] Generar SECRET_KEY largo y aleatorio
- [ ] Configurar dominio con SSL (HTTPS)
- [ ] Configurar firewall (solo puertos 80/443)
- [ ] Habilitar rate limiting
- [ ] Configurar backups automáticos
- [ ] Configurar alertas de CloudWatch

### Monitoreo Recomendado

```python
# Health check endpoint
@app.route('/health')
def health():
    return {
        'status': 'healthy',
        'dynamodb': 'connected',
        's3': 'connected'
    }
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT.

---

## 🤝 Contribuciones

1. Fork del repositorio
2. Crear rama feature (`git checkout -b feature/nueva-caracteristica`)
3. Commit de cambios (`git commit -am 'Agregar nueva característica'`)
4. Push a la rama (`git push origin feature/nueva-caracteristica`)
5. Crear Pull Request

---

## 📞 Soporte

Para soporte, crear un issue en el repositorio o contactar al equipo de desarrollo.

---

**Última actualización:** Documentación unificada
**Versión:** 1.0.0

