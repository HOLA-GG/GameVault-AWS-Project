#!/usr/bin/env python3
"""Recrea la tabla de password reset con índices y TTL profesionales."""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError

DYNAMODB_REGION = os.environ.get('AWS_REGION', 'us-east-1')
TABLE_NAME = os.environ.get('DYNAMODB_RESET_TABLE', 'GameVaultPasswordReset')
RESET_TOKEN_INDEX = os.environ.get('DYNAMODB_RESET_TOKEN_INDEX', 'reset-token-index')


def eliminar_tabla_si_existe(dynamodb):
    """Elimina la tabla anterior si existe."""
    try:
        tabla = dynamodb.Table(TABLE_NAME)
        tabla.delete()
        print(f"⏳ Eliminando tabla {TABLE_NAME}...")
        tabla.wait_until_not_exists()
        print(f"✅ Tabla {TABLE_NAME} eliminada")
        return True
    except ClientError as exc:
        if exc.response['Error']['Code'] == 'ResourceNotFoundException':
            print(f"ℹ️ Tabla {TABLE_NAME} no existe")
            return True
        print(f"❌ Error al eliminar tabla: {exc.response['Error']['Message']}")
        return False


def crear_tabla_password_reset(dynamodb):
    """Crea la tabla con índices por usuario y por reset_token."""
    try:
        tabla = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{'AttributeName': 'token_id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[
                {'AttributeName': 'token_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'reset_token', 'AttributeType': 'S'},
            ],
            GlobalSecondaryIndexes=[
                {
                    'IndexName': 'user_id-index',
                    'KeySchema': [{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': RESET_TOKEN_INDEX,
                    'KeySchema': [{'AttributeName': 'reset_token', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        print(f"⏳ Creando tabla {TABLE_NAME}...")
        tabla.wait_until_exists()
        print(f"✅ Tabla {TABLE_NAME} creada")
        return True
    except ClientError as exc:
        print(f"❌ Error al crear tabla: {exc.response['Error']['Message']}")
        return False


def habilitar_ttl(dynamodb_client):
    """Activa TTL sobre el atributo ttl."""
    try:
        dynamodb_client.update_time_to_live(
            TableName=TABLE_NAME,
            TimeToLiveSpecification={'Enabled': True, 'AttributeName': 'ttl'},
        )
        print("✅ TTL solicitado en el atributo 'ttl'")
    except ClientError as exc:
        print(f"⚠️ No se pudo activar TTL: {exc.response['Error']['Message']}")


def main():
    print('🚀 Migración de password reset para GameVault')
    print(f'📍 Región: {DYNAMODB_REGION}')
    print(f'📋 Tabla: {TABLE_NAME}')
    print(f'📋 Índice token: {RESET_TOKEN_INDEX}')
    print()

    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=DYNAMODB_REGION)

    print('🔄 Paso 1: eliminando tabla anterior')
    if not eliminar_tabla_si_existe(dynamodb):
        return

    print('\n🔄 Paso 2: creando tabla nueva')
    if not crear_tabla_password_reset(dynamodb):
        return

    print('\n🔄 Paso 3: activando TTL')
    habilitar_ttl(dynamodb_client)

    print('\n✅ Migración completada')
    print("   - 'reset_token' reemplaza el atributo antiguo reservado")
    print("   - Hay búsqueda directa por token mediante GSI")
    print("   - Los tokens pueden expirar automáticamente con TTL")


if __name__ == '__main__':
    main()
