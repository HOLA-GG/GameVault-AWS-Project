#!/usr/bin/env python3
"""
Script de Setup para DynamoDB - GameVault
Crea las tablas necesarias para la aplicación.
"""

import boto3
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash

DYNAMODB_REGION = 'us-east-1'

# Credenciales del administrador por defecto
ADMIN_EMAIL = 'admin@gamevault.com'
ADMIN_PASSWORD = 'admin123'  # Contraseña en texto plano
ADMIN_NOMBRE = 'Super Admin'
ADMIN_TELEFONO = '+0000000000'


def crear_tabla_juegos(dynamodb):
    """Crea la tabla GameVault para almacenar juegos."""
    try:
        tabla = dynamodb.create_table(
            TableName='GameVault',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},  # Partition Key
                {'AttributeName': 'game_id', 'KeyType': 'RANGE'}  # Sort Key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'game_id', 'AttributeType': 'S'}
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("⏳ Creando tabla GameVault...")
        tabla.wait_until_exists()
        print("✅ Tabla GameVault creada exitosamente!")
        return True
    except ClientError as e:
        print(f"❌ Error al crear tabla GameVault: {e.response['Error']['Message']}")
        return False


def crear_tabla_usuarios(dynamodb):
    """Crea la tabla GameVaultUsers con índice secundario global para email."""
    try:
        tabla = dynamodb.create_table(
            TableName='GameVaultUsers',
            KeySchema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'}  # Partition Key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [
                        {'AttributeName': 'email', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("⏳ Creando tabla GameVaultUsers...")
        tabla.wait_until_exists()
        print("✅ Tabla GameVaultUsers creada exitosamente!")
        return True
    except ClientError as e:
        print(f"❌ Error al crear tabla GameVaultUsers: {e.response['Error']['Message']}")
        return False


def crear_tabla_password_reset(dynamodb):
    """Crea la tabla GameVaultPasswordReset para tokens de recuperación de contraseña."""
    try:
        tabla = dynamodb.create_table(
            TableName='GameVaultPasswordReset',
            KeySchema=[
                {'AttributeName': 'token_id', 'KeyType': 'HASH'}  # Partition Key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'token_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("⏳ Creando tabla GameVaultPasswordReset...")
        tabla.wait_until_exists()
        print("✅ Tabla GameVaultPasswordReset creada exitosamente!")
        return True
    except ClientError as e:
        print(f"❌ Error al crear tabla GameVaultPasswordReset: {e.response['Error']['Message']}")
        return False


def crear_tabla_audit_logs(dynamodb):
    """Crea la tabla GameVaultAuditLogs para logs de auditoría."""
    try:
        tabla = dynamodb.create_table(
            TableName='GameVaultAuditLogs',
            KeySchema=[
                {'AttributeName': 'audit_id', 'KeyType': 'HASH'}  # Partition Key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'audit_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'}
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'}
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                    'ProvisionedThroughput': {
                        'ReadCapacityUnits': 5,
                        'WriteCapacityUnits': 5
                    }
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print("⏳ Creando tabla GameVaultAuditLogs...")
        tabla.wait_until_exists()
        print("✅ Tabla GameVaultAuditLogs creada exitosamente!")
        return True
    except ClientError as e:
        print(f"❌ Error al crear tabla GameVaultAuditLogs: {e.response['Error']['Message']}")
        return False


def verificar_todas_tablas(dynamodb):
    """Verifica todas las tablas requeridas por la aplicación."""
    tablas = [
        'GameVault',
        'GameVaultUsers',
        'GameVaultPasswordReset',
        'GameVaultAuditLogs'
    ]
    existentes = []
    
    for tabla in tablas:
        try:
            dynamodb.Table(tabla).load()
            existentes.append(tabla)
            print(f"✅ Tabla '{tabla}' ya existe")
        except ClientError:
            print(f"⚠️ Tabla '{tabla}' no existe")
        except Exception as e:
            print(f"⚠️ Error al verificar '{tabla}': {str(e)}")
    
    return existentes


def inyectar_admin_user(dynamodb):
    """
    Inyecta un usuario administrador por defecto si no existe.
    
    Returns:
        bool: True si se injectó o ya existía, False si hubo error
    """
    try:
        tabla = dynamodb.Table('GameVaultUsers')
        
        # Verificar si el admin ya existe
        import uuid
        from botocore.exceptions import ClientError
        
        # Buscar por email usando el índice
        try:
            response = tabla.query(
                IndexName='email-index',
                KeyConditionExpression='email = :email',
                ExpressionAttributeValues={
                    ':email': ADMIN_EMAIL
                }
            )
            items = response.get('Items', [])
            
            if items:
                # El admin ya existe, actualizar su rol
                admin_user = items[0]
                if admin_user.get('role') != 'admin':
                    tabla.update_item(
                        Key={'user_id': admin_user['user_id']},
                        UpdateExpression='SET role = :role',
                        ExpressionAttributeValues={':role': 'admin'}
                    )
                    print(f"✅ Admin actualizado: {ADMIN_EMAIL}")
                else:
                    print(f"✅ Admin ya existe: {ADMIN_EMAIL}")
                return True
                
        except ClientError as e:
            if e.response['Error']['Code'] != 'ValidationException':
                raise
        
        # Crear nuevo usuario admin
        user_id = str(uuid.uuid4())
        password_hash = generate_password_hash(ADMIN_PASSWORD)
        
        item = {
            'user_id': user_id,
            'email': ADMIN_EMAIL,
            'nombre': ADMIN_NOMBRE,
            'apellido': 'Admin',  # Apellido por defecto
            'prefijo_pais': '+000',
            'telefono': ADMIN_TELEFONO,
            'password_hash': password_hash,
            'role': 'admin'
        }
        
        tabla.put_item(Item=item)
        print(f"✅ Admin creado exitosamente: {ADMIN_EMAIL}")
        print(f"   Password: {ADMIN_PASSWORD}")
        return True
        
    except ClientError as e:
        print(f"❌ Error al injectar admin: {e.response['Error']['Message']}")
        return False
    except Exception as e:
        print(f"❌ Error inesperado al injectar admin: {str(e)}")
        return False


def main():
    print("🚀 Configurando DynamoDB para GameVault...")
    print(f"📍 Región: {DYNAMODB_REGION}")
    
    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    
    # Verificar tablas existentes
    existentes = verificar_todas_tablas(dynamodb)
    
    # Crear tabla de juegos si no existe
    if 'GameVault' not in existentes:
        crear_tabla_juegos(dynamodb)
    else:
        print("➡️ Tabla GameVault saltada (ya existe)")
    
    # Crear tabla de usuarios si no existe
    if 'GameVaultUsers' not in existentes:
        crear_tabla_usuarios(dynamodb)
    else:
        print("➡️ Tabla GameVaultUsers saltada (ya existe)")
    
    # Crear tabla de password reset si no existe
    if 'GameVaultPasswordReset' not in existentes:
        crear_tabla_password_reset(dynamodb)
    else:
        print("➡️ Tabla GameVaultPasswordReset saltada (ya existe)")
    
    # Crear tabla de audit logs si no existe
    if 'GameVaultAuditLogs' not in existentes:
        crear_tabla_audit_logs(dynamodb)
    else:
        print("➡️ Tabla GameVaultAuditLogs saltada (ya existe)")
    
    # Injectar usuario administrador
    print("\n👤 Configurando usuario administrador...")
    inyectar_admin_user(dynamodb)
    
    print("\n🎉 Configuración de DynamoDB completada!")
    print("\n📋 Tablas creadas:")
    print("   - GameVault (juegos)")
    print("   - GameVaultUsers (usuarios)")
    print("   - GameVaultPasswordReset (tokens de recuperación)")
    print("   - GameVaultAuditLogs (logs de auditoría)")


if __name__ == '__main__':
    main()

