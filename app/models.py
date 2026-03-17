"""
app/models.py - Capa de Datos Multi-Tenant para GameVault
Maneja conexión y operaciones con Amazon DynamoDB y S3
Esquema: Partition Key=user_id, Sort Key=game_id

Incluye:
- Operaciones de Juegos (CRUD)
- Gestión de Usuarios y Auth
- Password Reset Flow
- Audit Logs (Logs de Auditoría)
"""

import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import boto3
from boto3.dynamodb.conditions import Attr, Key
from botocore.client import Config
from botocore.exceptions import ClientError


# ================================
# CONFIGURACIÓN
# ================================

RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', 30))
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 90))
RESET_TOKEN_INDEX_NAME = os.environ.get('DYNAMODB_RESET_TOKEN_INDEX', 'reset-token-index')
AUDIT_TIMESTAMP_INDEX_NAME = os.environ.get('DYNAMODB_AUDIT_TIMESTAMP_INDEX', 'scope-timestamp-index')
AUDIT_LOG_SCOPE = 'global'


def utcnow() -> datetime:
    """Obtiene el tiempo actual en UTC."""
    return datetime.now(timezone.utc)


def iso_now() -> str:
    """Serializa el tiempo actual en UTC."""
    return utcnow().isoformat()


def future_unix_timestamp(minutes: int = 0, days: int = 0) -> int:
    """Calcula un timestamp UNIX futuro para usar como TTL."""
    return int((utcnow() + timedelta(minutes=minutes, days=days)).timestamp())


def get_dynamodb_table():
    """Obtiene la tabla de DynamoDB configurada."""
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.environ.get('AWS_REGION', 'us-east-1'),
        config=Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
    )
    return dynamodb.Table(os.environ.get('DYNAMODB_TABLE', 'GameVault'))


def get_dynamodb_users_table():
    """Obtiene la tabla de usuarios de DynamoDB."""
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
    return dynamodb.Table(os.environ.get('DYNAMODB_USERS_TABLE', 'GameVaultUsers'))


def get_s3_client():
    """Obtiene el cliente de S3."""
    return boto3.client(
        's3',
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )


# ================================
# UTILIDADES DE VALIDACIÓN
# ================================

def validar_email(email):
    """Valida el formato del email."""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None


def validar_telefono(telefono):
    """Valida que el teléfono contenga solo dígitos."""
    return telefono.isdigit() and len(telefono) >= 7 and len(telefono) <= 15


def validar_password(password):
    """Valida que la contraseña cumpla requisitos mínimos."""
    return len(password) >= 8  # Mínimo 8 caracteres


# ================================
# OPERACIONES S3
# ================================

def eliminar_imagen_s3(imagen_url):
    """
    Elimina una imagen del bucket S3.
    
    Args:
        imagen_url (str): URL completa de la imagen en S3
    
    Returns:
        bool: True si se eliminó, False si hubo error
    """
    try:
        # Extraer el nombre de la clave (key) de la URL
        # Formato: https://bucket.s3.region.amazonaws.com/key
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
        
        # Parsear la URL para obtener la key
        key = obtener_key_desde_url(imagen_url)
        
        if not key:
            print("⚠️ No se pudo extraer la key de la URL")
            return False
        
        # Eliminar el objeto de S3
        s3_client = get_s3_client()
        s3_client.delete_object(
            Bucket=bucket_name,
            Key=key
        )
        
        print(f"✅ Imagen eliminada de S3: {key}")
        return True
        
    except ClientError as e:
        print(f"❌ Error de S3 al eliminar imagen: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al eliminar imagen: {str(e)}")
        return False


def obtener_key_desde_url(imagen_url):
    """
    Extrae la key (nombre del objeto) desde una URL de S3.
    
    Args:
        imagen_url (str): URL completa del objeto en S3
    
    Returns:
        str: La key del objeto o None si no se puede extraer
    """
    try:
        bucket_name = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
        
        # Diferentes formatos de URL de S3
        if '.s3.' in imagen_url and '.amazonaws.com' in imagen_url:
            # Formato: https://bucket.s3.region.amazonaws.com/key
            return imagen_url.split(f'{bucket_name}.s3.')[1].split('.amazonaws.com/')[-1]
        elif 'amazonaws.com/' in imagen_url:
            # Formato alternativo
            return imagen_url.split('amazonaws.com/')[-1]
        else:
            # Asumir que es solo la key
            return imagen_url
            
    except Exception as e:
        print(f"❌ Error al parsear URL: {str(e)}")
        return None


def crear_url_firmada_lectura(imagen_url: str, expires_in: int = 3600) -> str:
    """Genera una URL temporal para mostrar una imagen privada de S3."""
    try:
        if not imagen_url:
            return imagen_url

        key = obtener_key_desde_url(imagen_url)
        if not key:
            return imagen_url

        bucket_name = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
        s3_client = get_s3_client()
        return s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key},
            ExpiresIn=expires_in,
        )
    except Exception as e:
        print(f"⚠️ No se pudo firmar la imagen para lectura: {str(e)}")
        return imagen_url


# ================================
# OPERACIONES DE JUEGOS (CRUD)
# ================================

def crear_juego(user_id, game_id, titulo, descripcion, imagen_url, plataforma='PC', estado='N/A'):
    """
    Guarda un nuevo juego en la tabla DynamoDB.
    
    Args:
        user_id (str): Identificador del usuario/tenant (Partition Key)
        game_id (str): Identificador único del juego (Sort Key)
        titulo (str): Nombre del juego
        descripcion (str): Descripción del juego
        imagen_url (str): URL pública de la imagen en S3
        plataforma (str): Plataforma del juego (PC, PlayStation, Xbox, Nintendo, Mobile, Otro)
        estado (str): Estado del juego (Nuevo, Como Nuevo, Bueno, Regular, N/A)
    
    Returns:
        dict: El item creado o None si hay error
    """
    try:
        tabla = get_dynamodb_table()
        
        timestamp = iso_now()
        item = {
            'user_id': user_id,
            'game_id': game_id,
            'titulo': titulo,
            'descripcion': descripcion,
            'imagen_url': imagen_url,
            'plataforma': plataforma,
            'estado': estado,
            'created_at': timestamp,
            'updated_at': timestamp,
        }
        
        response = tabla.put_item(Item=item)
        
        print(f"✅ Juego '{titulo}' guardado para usuario {user_id} con ID: {game_id}")
        return item
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al crear juego: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al crear juego: {str(e)}")
        return None


def obtener_juegos_por_usuario(user_id):
    """
    Obtiene todos los juegos de un usuario específico.
    USA QUERY (eficiente) - NO SCAN (prohibido en producción).
    
    Args:
        user_id (str): Identificador del usuario (Partition Key)
    
    Returns:
        list: Lista de diccionarios con los datos de cada juego
    """
    try:
        tabla = get_dynamodb_table()
        
        response = tabla.query(
            KeyConditionExpression=Key('user_id').eq(user_id)
        )
        
        juegos = response.get('Items', [])
        print(f"✅ Usuario {user_id} tiene {len(juegos)} juegos en DynamoDB")
        return juegos
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener juegos: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"❌ Error inesperado al obtener juegos: {str(e)}")
        return []


def obtener_juego_por_id(user_id, game_id):
    """
    Obtiene un juego específico por su ID y usuario.
    
    Args:
        user_id (str): Identificador del usuario (Partition Key)
        game_id (str): Identificador del juego (Sort Key)
    
    Returns:
        dict: Datos del juego o None si no existe
    """
    try:
        tabla = get_dynamodb_table()
        
        response = tabla.get_item(
            Key={
                'user_id': user_id,
                'game_id': game_id
            }
        )
        juego = response.get('Item')
        
        if juego:
            print(f"✅ Juego encontrado: {game_id} para usuario {user_id}")
        else:
            print(f"⚠️ Juego no encontrado: {game_id}")
        
        return juego
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB: {e.response['Error']['Message']}")
        return None


def eliminar_juego(user_id, game_id):
    """
    Elimina un juego de DynamoDB Y elimina la imagen de S3.
    IMPORTANTE: Primero elimina la imagen de S3, luego el item de DynamoDB.
    
    Args:
        user_id (str): Identificador del usuario (Partition Key)
        game_id (str): Identificador del juego (Sort Key)
    
    Returns:
        dict: {'success': bool, 'juego': dict o None, 'error': str o None}
    """
    try:
        # Paso 1: Obtener el juego para saber la URL de la imagen
        juego = obtener_juego_por_id(user_id, game_id)
        
        if juego is None:
            return {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        
        # Paso 2: Eliminar la imagen de S3 PRIMERO
        imagen_url = juego.get('imagen_url')
        s3_eliminada = True
        
        if imagen_url:
            s3_eliminada = eliminar_imagen_s3(imagen_url)
            if not s3_eliminada:
                print(f"⚠️ No se pudo eliminar la imagen de S3: {imagen_url}")
                # Continuamos con la eliminación de DynamoDB aunque falle S3
        
        # Paso 3: Eliminar el item de DynamoDB
        tabla = get_dynamodb_table()
        response = tabla.delete_item(
            Key={
                'user_id': user_id,
                'game_id': game_id
            }
        )
        
        print(f"✅ Juego {game_id} eliminado para usuario {user_id}")
        return {'success': True, 'juego': juego, 's3_eliminada': s3_eliminada}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al eliminar: {e.response['Error']['Message']}")
        return {'success': False, 'juego': None, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al eliminar: {str(e)}")
        return {'success': False, 'juego': None, 'error': str(e)}


def actualizar_juego(user_id, game_id, nuevos_datos, nueva_imagen=None):
    """
    Actualiza un juego existente.
    Si viene una nueva imagen, elimina la anterior de S3 y sube la nueva.
    
    Args:
        user_id (str): Identificador del usuario
        game_id (str): Identificador del juego
        nuevos_datos (dict): Diccionario con 'titulo' y/o 'descripcion'
        nueva_imagen: Objeto file de Flask (opcional)
    
    Returns:
        dict: {'success': bool, 'juego': dict o None, 'error': str o None}
    """
    try:
        # Paso 1: Verificar que el juego existe
        juego_actual = obtener_juego_por_id(user_id, game_id)
        
        if juego_actual is None:
            return {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        
        # Paso 2: Manejar nueva imagen si viene
        nueva_url = juego_actual.get('imagen_url')  # Mantener la actual por defecto
        imagen_anterior_url = juego_actual.get('imagen_url')
        
        if isinstance(nueva_imagen, str) and nueva_imagen:
            nueva_url = nueva_imagen
            if imagen_anterior_url and imagen_anterior_url != nueva_url:
                eliminar_imagen_s3(imagen_anterior_url)
        elif nueva_imagen:
            # Subir nueva imagen a S3
            from app.routes import subir_imagen_a_s3
            nueva_url = subir_imagen_a_s3(nueva_imagen)
            
            if nueva_url is None:
                return {'success': False, 'juego': None, 'error': 'Error al subir nueva imagen'}
            
            # Eliminar imagen anterior de S3
            if imagen_anterior_url:
                eliminar_imagen_s3(imagen_anterior_url)
        
        # Paso 3: Actualizar en DynamoDB
        tabla = get_dynamodb_table()
        
        # Construir expresión de actualización
        update_expression = "SET imagen_url = :url, updated_at = :updated_at"
        expression_attributes = {
            ':url': nueva_url,
            ':updated_at': iso_now(),
        }
        
        if 'titulo' in nuevos_datos and nuevos_datos['titulo']:
            update_expression += ", titulo = :titulo"
            expression_attributes[':titulo'] = nuevos_datos['titulo']
        
        if 'descripcion' in nuevos_datos and nuevos_datos['descripcion']:
            update_expression += ", descripcion = :desc"
            expression_attributes[':desc'] = nuevos_datos['descripcion']
        
        if 'plataforma' in nuevos_datos:
            update_expression += ", plataforma = :plataforma"
            expression_attributes[':plataforma'] = nuevos_datos['plataforma']
        
        if 'estado' in nuevos_datos:
            update_expression += ", estado = :estado"
            expression_attributes[':estado'] = nuevos_datos['estado']
        
        # Ejecutar actualización
        response = tabla.update_item(
            Key={
                'user_id': user_id,
                'game_id': game_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attributes,
            ReturnValues='ALL_NEW'
        )
        
        juego_actualizado = response.get('Attributes', {})
        print(f"✅ Juego {game_id} actualizado para usuario {user_id}")
        
        return {'success': True, 'juego': juego_actualizado, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al actualizar: {e.response['Error']['Message']}")
        return {'success': False, 'juego': None, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al actualizar: {str(e)}")
        return {'success': False, 'juego': None, 'error': str(e)}


# ================================
# FUNCIONES DE USUARIO (AUTH)
# ================================

def crear_usuario(nombre, apellido, email, prefijo_pais, telefono, password_hash):
    """
    Crea un nuevo usuario en la tabla GameVaultUsers.
    
    Args:
        nombre (str): Nombre del usuario
        apellido (str): Apellidos del usuario
        email (str): Correo electrónico único
        prefijo_pais (str): Prefijo del país (ej: +52, +34)
        telefono (str): Número de teléfono
        password_hash (str): Hash de la contraseña
    
    Returns:
        dict: El usuario creado o None si hay error
    """
    try:
        tabla = get_dynamodb_users_table()
        
        # Generar ID único para el usuario
        user_id = str(uuid.uuid4())
        
        timestamp = iso_now()
        item = {
            'user_id': user_id,
            'email': email.lower().strip(),
            'nombre': nombre.strip(),
            'apellido': (apellido or '').strip(),
            'prefijo_pais': (prefijo_pais or '').strip(),
            'telefono': (telefono or '').strip(),
            'password_hash': password_hash,
            'role': 'user',
            'status': 'active',
            'created_at': timestamp,
            'updated_at': timestamp,
        }
        
        response = tabla.put_item(Item=item)
        
        print(f"✅ Usuario '{email}' creado exitosamente con ID: {user_id}")
        return item
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al crear usuario: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al crear usuario: {str(e)}")
        return None


def obtener_usuario_por_email(email):
    """
    Obtiene un usuario por su email.
    
    Args:
        email (str): Correo electrónico del usuario
    
    Returns:
        dict: Datos del usuario o None si no existe
    """
    try:
        tabla = get_dynamodb_users_table()
        
        response = tabla.query(
            IndexName='email-index',
            KeyConditionExpression=Key('email').eq(email.lower().strip())
        )
        
        items = response.get('Items', [])
        
        if items:
            print(f"✅ Usuario encontrado: {email}")
            return items[0]
        else:
            print(f"⚠️ Usuario no encontrado: {email}")
            return None
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al buscar usuario: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al buscar usuario: {str(e)}")
        return None


def verificar_credenciales(email, password):
    """
    Verifica las credenciales de un usuario.
    
    Args:
        email (str): Correo electrónico
        password (str): Contraseña en texto plano
    
    Returns:
        dict: Datos del usuario si son válidas, None si no
    """
    try:
        usuario = obtener_usuario_por_email(email)
        
        if usuario is None:
            print(f"❌ Login fallido: usuario no existe - {email}")
            return None
        
        return usuario
        
    except Exception as e:
        print(f"❌ Error al verificar credenciales: {str(e)}")
        return None


def obtener_todos_usuarios():
    """
    Obtiene todos los usuarios de la tabla (SCAN - usar con cuidado en producción).
    
    Returns:
        list: Lista de todos los usuarios
    """
    try:
        tabla = get_dynamodb_users_table()
        
        response = tabla.scan()
        usuarios = response.get('Items', [])
        
        # Manejar paginación si hay más de 1MB de datos
        while 'LastEvaluatedKey' in response:
            response = tabla.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
            usuarios.extend(response.get('Items', []))
        
        print(f"✅ Total de usuarios encontrados: {len(usuarios)}")
        return usuarios
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener usuarios: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"❌ Error inesperado al obtener usuarios: {str(e)}")
        return []


def eliminar_usuario(user_id):
    """
    Elimina un usuario de la tabla.
    
    Args:
        user_id (str): ID del usuario a eliminar
    
    Returns:
        dict: {'success': bool, 'error': str o None}
    """
    try:
        tabla = get_dynamodb_users_table()
        
        response = tabla.delete_item(
            Key={'user_id': user_id}
        )
        
        print(f"✅ Usuario {user_id} eliminado")
        return {'success': True, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al eliminar usuario: {e.response['Error']['Message']}")
        return {'success': False, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al eliminar usuario: {str(e)}")
        return {'success': False, 'error': str(e)}


def actualizar_usuario_nombre(user_id, nombre):
    """
    Actualiza el nombre de un usuario.
    
    Args:
        user_id (str): ID del usuario
        nombre (str): Nuevo nombre
    
    Returns:
        dict: {'success': bool, 'error': str o None}
    """
    try:
        tabla = get_dynamodb_users_table()
        
        response = tabla.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET nombre = :nombre, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':nombre': nombre.strip(),
                ':updated_at': iso_now(),
            },
            ReturnValues='ALL_NEW'
        )
        
        print(f"✅ Usuario {user_id} actualizado con nombre: {nombre}")
        return {'success': True, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al actualizar usuario: {e.response['Error']['Message']}")
        return {'success': False, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al actualizar usuario: {str(e)}")
        return {'success': False, 'error': str(e)}


# ================================
# CONFIGURACIÓN ADICIONAL
# ================================

def get_dynamodb_reset_table():
    """Obtiene la tabla de tokens de recuperación de contraseña."""
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
    return dynamodb.Table(os.environ.get('DYNAMODB_RESET_TABLE', 'GameVaultPasswordReset'))


def get_dynamodb_audit_table():
    """Obtiene la tabla de logs de auditoría."""
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
    return dynamodb.Table(os.environ.get('DYNAMODB_AUDIT_TABLE', 'GameVaultAuditLogs'))


# ================================
# PASSWORD RESET FLOW
# ================================

def crear_reset_token(user_id: str, ip_address: str = None) -> Dict[str, Any]:
    """
    Crea un token seguro para recuperación de contraseña.
    
    Args:
        user_id (str): ID del usuario que solicita el reset
        ip_address (str): IP del cliente (opcional)
    
    Returns:
        dict: {'success': bool, 'token': str, 'expires_at': datetime, 'error': str}
    """
    try:
        tabla = get_dynamodb_reset_table()
        
        # Generar token seguro (UUID + random bytes)
        token_id = str(uuid.uuid4())
        reset_token = f"{secrets.token_urlsafe(32)}"
        
        now = utcnow()
        expires_at = now + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
        
        item = {
            'token_id': token_id,
            'user_id': user_id,
            'reset_token': reset_token,  # Usar 'reset_token' en lugar de 'token' (palabra reservada)
            'created_at': now.isoformat(),
            'expires_at': expires_at.isoformat(),
            'expires_at_unix': int(expires_at.timestamp()),
            'used': False,
            'ip_address': ip_address or 'unknown',
            'ttl': int(expires_at.timestamp()),
        }
        
        tabla.put_item(Item=item)
        
        print(f"✅ Token de reset creado para usuario {user_id}")
        return {
            'success': True,
            'token': reset_token,
            'expires_at': expires_at,
            'error': None
        }
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al crear token: {e.response['Error']['Message']}")
        return {'success': False, 'token': None, 'expires_at': None, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al crear token: {str(e)}")
        return {'success': False, 'token': None, 'expires_at': None, 'error': str(e)}


def validar_reset_token(reset_token: str) -> Dict[str, Any]:
    """
    Valida un token de recuperación de contraseña.
    
    Args:
        reset_token (str): Token a validar
    
    Returns:
        dict: {'valid': bool, 'user_id': str, 'error': str}
    """
    try:
        items = obtener_token_por_valor(reset_token, only_active=True)
        
        if not items:
            return {'valid': False, 'user_id': None, 'error': 'Token no encontrado o ya utilizado'}
        
        item = items[0]
        
        # Verificar expiración
        expires_at = datetime.fromisoformat(item['expires_at'])
        now = utcnow()
        
        if expires_at < now:
            return {'valid': False, 'user_id': None, 'error': 'Token expirado'}
        
        return {
            'valid': True,
            'user_id': item['user_id'],
            'error': None
        }
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al validar token: {e.response['Error']['Message']}")
        return {'valid': False, 'user_id': None, 'error': 'Error al validar token'}
    except Exception as e:
        print(f"❌ Error inesperado al validar token: {str(e)}")
        return {'valid': False, 'user_id': None, 'error': str(e)}


def usar_token(reset_token: str) -> Dict[str, Any]:
    """
    Marca un token como usado después de un cambio de contraseña exitoso.
    
    Args:
        reset_token (str): Token a marcar como usado
    
    Returns:
        dict: {'success': bool, 'error': str}
    """
    try:
        tabla = get_dynamodb_reset_table()
        items = obtener_token_por_valor(reset_token, only_active=False)
        
        if not items:
            return {'success': False, 'error': 'Token no encontrado'}
        
        item = items[0]
        token_id = item['token_id']
        
        # Marcar como usado
        tabla.update_item(
            Key={'token_id': token_id},
            UpdateExpression='SET used = :used, used_at = :used_at',
            ExpressionAttributeValues={
                ':used': True,
                ':used_at': iso_now(),
            }
        )
        
        print(f"✅ Token marcado como usado: {token_id}")
        return {'success': True, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al usar token: {e.response['Error']['Message']}")
        return {'success': False, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al usar token: {str(e)}")
        return {'success': False, 'error': str(e)}


def obtener_token_por_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    Obtiene el token activo más reciente de un usuario.
    
    Args:
        user_id (str): ID del usuario
    
    Returns:
        dict: Token activo o None
    """
    try:
        tabla = get_dynamodb_reset_table()
        
        response = tabla.query(
            IndexName='user_id-index',
            KeyConditionExpression=Key('user_id').eq(user_id),
            Limit=1,
            ScanIndexForward=False  # Más reciente primero
        )
        
        items = response.get('Items', [])
        
        if items:
            # Verificar que no esté usado ni expirado
            item = items[0]
            if not item.get('used', False):
                expires_at = datetime.fromisoformat(item['expires_at'])
                if expires_at > utcnow():
                    return item
        
        return None
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener token: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al obtener token: {str(e)}")
        return None


def eliminar_tokens_expirados() -> Dict[str, Any]:
    """
    Elimina tokens expirados de la tabla.
    Debería ejecutarse periódicamente (ej: mediante Lambda + CloudWatch).
    
    Returns:
        dict: {'deleted': int, 'error': str}
    """
    try:
        tabla = get_dynamodb_reset_table()
        
        now = iso_now()
        
        # Usar scan para encontrar tokens expirados (en producción usar TTL de DynamoDB)
        response = tabla.scan(
            FilterExpression='used = :used AND expires_at < :now',
            ExpressionAttributeValues={
                ':used': False,
                ':now': now
            }
        )
        
        items = response.get('Items', [])
        deleted = 0
        
        for item in items:
            tabla.delete_item(Key={'token_id': item['token_id']})
            deleted += 1
        
        print(f"✅ {deleted} tokens expirados eliminados")
        return {'deleted': deleted, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al limpiar tokens: {e.response['Error']['Message']}")
        return {'deleted': 0, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al limpiar tokens: {str(e)}")
        return {'deleted': 0, 'error': str(e)}


# ================================
# AUDIT LOGS (LOGS DE AUDITORÍA)
# ================================

AUDIT_ACTIONS = {
    'LOGIN': 'Inicio de sesión',
    'LOGOUT': 'Cierre de sesión',
    'REGISTER': 'Registro de usuario',
    'CREATE_GAME': 'Crear juego',
    'UPDATE_GAME': 'Actualizar juego',
    'DELETE_GAME': 'Eliminar juego',
    'PASSWORD_RESET_REQUEST': 'Solicitud de recuperacion',
    'PASSWORD_RESET': 'Recuperación de contraseña',
    'ADMIN_ACTION': 'Acción administrativa',
    'UPDATE_PROFILE': 'Actualizar perfil',
    'CHANGE_PASSWORD': 'Cambio de contraseña',
    'FAILED_LOGIN': 'Login fallido'
}


def crear_log_audit(
    user_id: str,
    action: str,
    resource: str,
    details: Dict[str, Any] = None,
    ip_address: str = None,
    user_agent: str = None,
    status: str = 'SUCCESS'
) -> Dict[str, Any]:
    """
    Crea un registro de auditoría para una acción.
    
    Args:
        user_id (str): ID del usuario que realizó la acción
        action (str): Tipo de acción (LOGIN, LOGOUT, CREATE, UPDATE, DELETE, etc.)
        resource (str): Recurso afectado (users, games, auth, etc.)
        details (dict): Detalles adicionales de la acción
        ip_address (str): IP del cliente
        user_agent (str): User agent del navegador
        status (str): Estado de la acción (SUCCESS, FAILED, ERROR)
    
    Returns:
        dict: {'success': bool, 'audit_id': str, 'error': str}
    """
    try:
        tabla = get_dynamodb_audit_table()
        
        audit_id = str(uuid.uuid4())
        timestamp = iso_now()
        
        item = {
            'audit_id': audit_id,
            'log_scope': AUDIT_LOG_SCOPE,
            'user_id': user_id,
            'action': action,
            'action_name': AUDIT_ACTIONS.get(action, action),
            'resource': resource,
            'timestamp': timestamp,
            'ip_address': ip_address or 'unknown',
            'user_agent': user_agent or 'unknown',
            'details': details or {},
            'status': status,
            'ttl': future_unix_timestamp(days=AUDIT_LOG_RETENTION_DAYS),
        }
        
        tabla.put_item(Item=item)
        
        print(f"✅ Audit log creado: {action} por usuario {user_id}")
        return {
            'success': True,
            'audit_id': audit_id,
            'error': None
        }
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al crear audit log: {e.response['Error']['Message']}")
        return {'success': False, 'audit_id': None, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al crear audit log: {str(e)}")
        return {'success': False, 'audit_id': None, 'error': str(e)}


def obtener_logs_por_usuario(
    user_id: str,
    limit: int = 50
) -> List[Dict[str, Any]]:
    """
    Obtiene los logs de auditoría de un usuario específico.
    
    Args:
        user_id (str): ID del usuario
        limit (int): Máximo número de logs a retornar
    
    Returns:
        list: Lista de logs de auditoría
    """
    try:
        tabla = get_dynamodb_audit_table()
        
        response = tabla.query(
            IndexName='user-timestamp-index',
            KeyConditionExpression=Key('user_id').eq(user_id),
            Limit=limit,
            ScanIndexForward=False  # Más recientes primero
        )
        
        return response.get('Items', [])
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener logs: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"❌ Error inesperado al obtener logs: {str(e)}")
        return []


def obtener_todos_logs(
    filters: Dict[str, Any] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los logs de auditoría con filtros opcionales.
    
    Args:
        filters (dict): Filtros aplicables (user_id, action, status, start_date, end_date)
        limit (int): Máximo número de logs a retornar
    
    Returns:
        list: Lista de logs de auditoría
    """
    try:
        tabla = get_dynamodb_audit_table()
        filters = filters or {}

        key_condition = Key('log_scope').eq(AUDIT_LOG_SCOPE)
        if filters.get('start_date') and filters.get('end_date'):
            key_condition = key_condition & Key('timestamp').between(
                filters['start_date'],
                filters['end_date'],
            )
        elif filters.get('start_date'):
            key_condition = key_condition & Key('timestamp').gte(filters['start_date'])
        elif filters.get('end_date'):
            key_condition = key_condition & Key('timestamp').lte(filters['end_date'])

        filter_expression = None
        if filters.get('user_id'):
            filter_expression = Attr('user_id').eq(filters['user_id'])
        if filters.get('action'):
            action_filter = Attr('action').eq(filters['action'])
            filter_expression = action_filter if filter_expression is None else filter_expression & action_filter
        if filters.get('status'):
            status_filter = Attr('status').eq(filters['status'])
            filter_expression = status_filter if filter_expression is None else filter_expression & status_filter

        try:
            query_args = {
                'IndexName': AUDIT_TIMESTAMP_INDEX_NAME,
                'KeyConditionExpression': key_condition,
                'Limit': limit,
                'ScanIndexForward': False,
            }
            if filter_expression is not None:
                query_args['FilterExpression'] = filter_expression
            response = tabla.query(**query_args)
            logs = response.get('Items', [])
        except ClientError as e:
            if e.response['Error']['Code'] != 'ValidationException':
                raise
            # Compatibilidad con tablas antiguas sin GSI nuevo.
            if filters:
                scan_filter_expression = None
                expression_values = {}

                if filters.get('user_id'):
                    scan_filter_expression = 'user_id = :user_id'
                    expression_values[':user_id'] = filters['user_id']
                if filters.get('action'):
                    expression_values[':action'] = filters['action']
                    scan_filter_expression = (
                        f'{scan_filter_expression} AND action = :action'
                        if scan_filter_expression
                        else 'action = :action'
                    )
                if filters.get('status'):
                    expression_values[':status'] = filters['status']
                    scan_filter_expression = (
                        f'{scan_filter_expression} AND status = :status'
                        if scan_filter_expression
                        else 'status = :status'
                    )
                if filters.get('start_date'):
                    expression_values[':start_date'] = filters['start_date']
                    scan_filter_expression = (
                        f'{scan_filter_expression} AND timestamp >= :start_date'
                        if scan_filter_expression
                        else 'timestamp >= :start_date'
                    )
                if filters.get('end_date'):
                    expression_values[':end_date'] = filters['end_date']
                    scan_filter_expression = (
                        f'{scan_filter_expression} AND timestamp <= :end_date'
                        if scan_filter_expression
                        else 'timestamp <= :end_date'
                    )

                response = tabla.scan(
                    FilterExpression=scan_filter_expression,
                    ExpressionAttributeValues=expression_values,
                    Limit=limit,
                ) if scan_filter_expression else tabla.scan(Limit=limit)
            else:
                response = tabla.scan(Limit=limit)
            logs = response.get('Items', [])

        # Ordenar por timestamp (más recientes primero)
        logs.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return logs[:limit]
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener todos los logs: {e.response['Error']['Message']}")
        return []
    except Exception as e:
        print(f"❌ Error inesperado al obtener todos los logs: {str(e)}")
        return []


def obtener_estadisticas_logs() -> Dict[str, Any]:
    """
    Obtiene estadísticas generales de los logs de auditoría.
    
    Returns:
        dict: Estadísticas del sistema
    """
    try:
        tabla = get_dynamodb_audit_table()
        
        response = tabla.scan()
        logs = response.get('Items', [])
        
        # Calcular estadísticas
        total_logs = len(logs)
        
        # Logs por acción
        action_counts = {}
        for log in logs:
            action = log.get('action', 'UNKNOWN')
            action_counts[action] = action_counts.get(action, 0) + 1
        
        # Logs por status
        status_counts = {}
        for log in logs:
            status = log.get('status', 'UNKNOWN')
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Logs por día (últimos 7 días)
        from collections import defaultdict
        daily_counts = defaultdict(int)
        
        for log in logs:
            timestamp = log.get('timestamp', '')
            if timestamp:
                try:
                    date = timestamp[:10]  # YYYY-MM-DD
                    daily_counts[date] += 1
                except:
                    pass
        
        # Últimos 7 días
        import datetime as dt
        last_7_days = []
        for i in range(7):
            date = (dt.datetime.now(timezone.utc) - dt.timedelta(days=i)).strftime('%Y-%m-%d')
            last_7_days.append({
                'date': date,
                'count': daily_counts.get(date, 0)
            })
        last_7_days.reverse()
        
        # Usuarios más activos
        user_counts = {}
        for log in logs:
            user_id = log.get('user_id', 'anonymous')
            user_counts[user_id] = user_counts.get(user_id, 0) + 1
        
        top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            'total_logs': total_logs,
            'action_counts': action_counts,
            'status_counts': status_counts,
            'daily_activity': last_7_days,
            'top_users': top_users,
            'success_rate': round(
                (status_counts.get('SUCCESS', 0) / total_logs * 100) 
                if total_logs > 0 else 100, 2
            )
        }
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener estadísticas: {e.response['Error']['Message']}")
        return {'error': str(e)}
    except Exception as e:
        print(f"❌ Error inesperado al obtener estadísticas: {str(e)}")
        return {'error': str(e)}


def limpiar_logs_antiguos(days: int = None) -> Dict[str, Any]:
    """
    Elimina logs de auditoría más antiguos que N días.
    Debería ejecutarse periódicamente mediante Lambda + CloudWatch.
    
    Args:
        days (int): Número de días de retención
    
    Returns:
        dict: {'deleted': int, 'error': str}
    """
    try:
        if days is None:
            days = AUDIT_LOG_RETENTION_DAYS
        
        tabla = get_dynamodb_audit_table()
        
        cutoff_date = (utcnow() - timedelta(days=days)).isoformat()
        
        # Buscar logs antiguos
        response = tabla.scan(
            FilterExpression='timestamp < :cutoff',
            ExpressionAttributeValues={
                ':cutoff': cutoff_date
            }
        )
        
        items = response.get('Items', [])
        deleted = 0
        
        for item in items:
            tabla.delete_item(Key={'audit_id': item['audit_id']})
            deleted += 1
        
        print(f"✅ {deleted} logs antiguos eliminados (mayores a {days} días)")
        return {'deleted': deleted, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al limpiar logs: {e.response['Error']['Message']}")
        return {'deleted': 0, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al limpiar logs: {str(e)}")
        return {'deleted': 0, 'error': str(e)}


def exportar_logs_csv(logs: List[Dict[str, Any]]) -> str:
    """
    Exporta una lista de logs a formato CSV.
    
    Args:
        logs (list): Lista de logs de auditoría
    
    Returns:
        str: Contenido CSV
    """
    import csv
    import io
    
    output = io.StringIO()
    fieldnames = ['audit_id', 'user_id', 'action', 'resource', 'timestamp', 'ip_address', 'status', 'details']
    
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    
    for log in logs:
        # Simplificar details para CSV
        row = {k: log.get(k, '') for k in fieldnames[:-1]}
        row['details'] = str(log.get('details', {}))
        writer.writerow(row)
    
    return output.getvalue()


def obtener_usuario_por_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por su identificador."""
    try:
        tabla = get_dynamodb_users_table()
        response = tabla.get_item(Key={'user_id': user_id})
        return response.get('Item')
    except ClientError as e:
        print(f"❌ Error de DynamoDB al obtener usuario por ID: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al obtener usuario por ID: {str(e)}")
        return None


def actualizar_usuario_perfil(user_id: str, cambios: Dict[str, str]) -> Dict[str, Any]:
    """Actualiza los datos básicos del perfil del usuario."""
    try:
        tabla = get_dynamodb_users_table()
        campos = []
        valores: Dict[str, Any] = {':updated_at': iso_now()}

        for field in ('nombre', 'apellido', 'prefijo_pais', 'telefono'):
            if field in cambios:
                key = f':{field}'
                campos.append(f'{field} = {key}')
                valores[key] = (cambios.get(field) or '').strip()

        if not campos:
            return {'success': True, 'error': None}

        update_expression = 'SET ' + ', '.join(campos) + ', updated_at = :updated_at'
        tabla.update_item(
            Key={'user_id': user_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=valores,
            ReturnValues='ALL_NEW',
        )
        return {'success': True, 'error': None}
    except ClientError as e:
        print(f"❌ Error de DynamoDB al actualizar perfil: {e.response['Error']['Message']}")
        return {'success': False, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al actualizar perfil: {str(e)}")
        return {'success': False, 'error': str(e)}


def actualizar_password_usuario(user_id: str, password_hash: str) -> Dict[str, Any]:
    """Actualiza la contraseña de un usuario."""
    try:
        tabla = get_dynamodb_users_table()
        tabla.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET password_hash = :password_hash, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':password_hash': password_hash,
                ':updated_at': iso_now(),
            },
            ReturnValues='ALL_NEW',
        )
        return {'success': True, 'error': None}
    except ClientError as e:
        print(f"❌ Error de DynamoDB al actualizar contraseña: {e.response['Error']['Message']}")
        return {'success': False, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al actualizar contraseña: {str(e)}")
        return {'success': False, 'error': str(e)}


def obtener_token_por_valor(reset_token: str, only_active: bool = True) -> List[Dict[str, Any]]:
    """Busca tokens por valor intentando usar un índice y degradando a scan si no existe."""
    tabla = get_dynamodb_reset_table()

    try:
        response = tabla.query(
            IndexName=RESET_TOKEN_INDEX_NAME,
            KeyConditionExpression=Key('reset_token').eq(reset_token),
            Limit=5,
            ScanIndexForward=False,
        )
        items = response.get('Items', [])
    except ClientError as e:
        if e.response['Error']['Code'] != 'ValidationException':
            raise
        response = tabla.scan(
            FilterExpression='reset_token = :reset_token',
            ExpressionAttributeValues={':reset_token': reset_token},
        )
        items = response.get('Items', [])

    if only_active:
        now = utcnow()
        items = [
            item
            for item in items
            if not item.get('used', False)
            and datetime.fromisoformat(item['expires_at']) > now
        ]
    return items


def crear_presigned_upload(nombre_archivo: str, content_type: str, max_upload_bytes: int) -> Dict[str, Any]:
    """Genera una URL firmada para que el navegador suba una imagen directo a S3."""
    bucket_name = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
    region_name = os.environ.get('AWS_REGION', 'us-east-1')
    extension = os.path.splitext(nombre_archivo)[1].lower()
    object_key = f"covers/{uuid.uuid4()}{extension}"
    s3_client = get_s3_client()

    response = s3_client.generate_presigned_post(
        Bucket=bucket_name,
        Key=object_key,
        Fields={'Content-Type': content_type},
        Conditions=[
            {'Content-Type': content_type},
            ['content-length-range', 1, max_upload_bytes],
        ],
        ExpiresIn=300,
    )

    return {
        'upload': response,
        'file_url': f"https://{bucket_name}.s3.{region_name}.amazonaws.com/{object_key}",
        'object_key': object_key,
    }
