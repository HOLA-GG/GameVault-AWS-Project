#!/usr/bin/env python3
"""
Script de Migración para GameVault Password Reset
Elimina la tabla antigua (con 'token') y crea una nueva (con 'reset_token')
"""

import boto3
from botocore.exceptions import ClientError
import time

DYNAMODB_REGION = 'us-east-1'
TABLE_NAME = 'GameVaultPasswordReset'


def eliminar_tabla_si_existe(dynamodb):
    """Elimina la tabla si existe."""
    try:
        tabla = dynamodb.Table(TABLE_NAME)
        tabla.delete()
        print(f"⏳ Eliminando tabla {TABLE_NAME}...")
        tabla.wait_until_not_exists()
        print(f"✅ Tabla {TABLE_NAME} eliminada")
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"ℹ️ Tabla {TABLE_NAME} no existe, no hay nada que eliminar")
            return True
        else:
            print(f"❌ Error al eliminar tabla: {e.response['Error']['Message']}")
            return False
    except Exception as e:
        print(f"❌ Error inesperado: {str(e)}")
        return False


def crear_tabla_password_reset(dynamodb):
    """Crea la tabla GameVaultPasswordReset con índice secundario para reset_token."""
    try:
        tabla = dynamodb.create_table(
            TableName=TABLE_NAME,
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
        print(f"   Nota: El atributo 'reset_token' ahora reemplaza 'token' (palabra reservada)")
        return True
    except ClientError as e:
        print(f"❌ Error al crear tabla GameVaultPasswordReset: {e.response['Error']['Message']}")
        return False


def main():
    print("🚀 Migración de Password Reset para GameVault...")
    print(f"📍 Región: {DYNAMODB_REGION}")
    print(f"📋 Tabla: {TABLE_NAME}")
    print()
    
    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    
    # Eliminar tabla existente
    print("🔄 Paso 1: Verificando tabla existente...")
    eliminar_tabla_si_existe(dynamodb)
    
    # Crear nueva tabla
    print()
    print("🔄 Paso 2: Creando nueva tabla con 'reset_token'...")
    crear_tabla_password_reset(dynamodb)
    
    print()
    print("✅ Migración completada!")
    print()
    print("📝 Cambios realizados:")
    print("   - Atributo 'token' reemplazado por 'reset_token'")
    print("   - Token expira en 3 minutos (configurable)")
    print("   - Los tokens expirados se eliminan automáticamente")


if __name__ == '__main__':
    main()

