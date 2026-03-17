#!/usr/bin/env python3
"""Provisiona DynamoDB para GameVault con un esquema apto para beta pública."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
from werkzeug.security import generate_password_hash

DYNAMODB_REGION = os.environ.get('AWS_REGION', 'us-east-1')
GAMES_TABLE = os.environ.get('DYNAMODB_TABLE', 'GameVault')
USERS_TABLE = os.environ.get('DYNAMODB_USERS_TABLE', 'GameVaultUsers')
RESET_TABLE = os.environ.get('DYNAMODB_RESET_TABLE', 'GameVaultPasswordReset')
AUDIT_TABLE = os.environ.get('DYNAMODB_AUDIT_TABLE', 'GameVaultAuditLogs')
RESET_TOKEN_INDEX = os.environ.get('DYNAMODB_RESET_TOKEN_INDEX', 'reset-token-index')
AUDIT_INDEX = os.environ.get('DYNAMODB_AUDIT_TIMESTAMP_INDEX', 'scope-timestamp-index')


def now_iso() -> str:
    """Fecha UTC serializada."""
    return datetime.now(timezone.utc).isoformat()


def common_table_args(table_name, key_schema, attribute_definitions, gsis=None):
    """Argumentos comunes para tablas on-demand."""
    args = {
        'TableName': table_name,
        'KeySchema': key_schema,
        'AttributeDefinitions': attribute_definitions,
        'BillingMode': 'PAY_PER_REQUEST',
    }
    if gsis:
        args['GlobalSecondaryIndexes'] = gsis
    return args


def create_table_if_missing(dynamodb, table_name, create_args):
    """Crea una tabla si aún no existe."""
    table = dynamodb.Table(table_name)
    try:
        table.load()
        print(f"✅ Tabla '{table_name}' ya existe")
        return table
    except ClientError as exc:
        if exc.response['Error']['Code'] != 'ResourceNotFoundException':
            raise

    print(f"⏳ Creando tabla '{table_name}'...")
    table = dynamodb.create_table(**create_args)
    table.wait_until_exists()
    print(f"✅ Tabla '{table_name}' creada")
    return table


def enable_ttl(dynamodb_client, table_name: str, attribute_name: str) -> None:
    """Activa TTL si aún no está habilitado."""
    try:
        description = dynamodb_client.describe_time_to_live(TableName=table_name)
        status = description.get('TimeToLiveDescription', {}).get('TimeToLiveStatus')
        if status in {'ENABLED', 'ENABLING'}:
            print(f"✅ TTL ya activo en '{table_name}' ({attribute_name})")
            return
        dynamodb_client.update_time_to_live(
            TableName=table_name,
            TimeToLiveSpecification={
                'Enabled': True,
                'AttributeName': attribute_name,
            },
        )
        print(f"✅ TTL solicitado para '{table_name}' usando '{attribute_name}'")
    except ClientError as exc:
        print(f"⚠️ No se pudo activar TTL en '{table_name}': {exc.response['Error']['Message']}")


def create_games_table(dynamodb):
    """Tabla de juegos por usuario."""
    return create_table_if_missing(
        dynamodb,
        GAMES_TABLE,
        common_table_args(
            GAMES_TABLE,
            key_schema=[
                {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                {'AttributeName': 'game_id', 'KeyType': 'RANGE'},
            ],
            attribute_definitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'game_id', 'AttributeType': 'S'},
            ],
        ),
    )


def create_users_table(dynamodb):
    """Tabla de usuarios con búsqueda por email."""
    return create_table_if_missing(
        dynamodb,
        USERS_TABLE,
        common_table_args(
            USERS_TABLE,
            key_schema=[{'AttributeName': 'user_id', 'KeyType': 'HASH'}],
            attribute_definitions=[
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'email', 'AttributeType': 'S'},
            ],
            gsis=[
                {
                    'IndexName': 'email-index',
                    'KeySchema': [{'AttributeName': 'email', 'KeyType': 'HASH'}],
                    'Projection': {'ProjectionType': 'ALL'},
                }
            ],
        ),
    )


def create_reset_table(dynamodb):
    """Tabla de recuperación con búsqueda por usuario y por token."""
    return create_table_if_missing(
        dynamodb,
        RESET_TABLE,
        common_table_args(
            RESET_TABLE,
            key_schema=[{'AttributeName': 'token_id', 'KeyType': 'HASH'}],
            attribute_definitions=[
                {'AttributeName': 'token_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'reset_token', 'AttributeType': 'S'},
            ],
            gsis=[
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
        ),
    )


def create_audit_table(dynamodb):
    """Tabla de auditoría con vistas por usuario y por tiempo global."""
    return create_table_if_missing(
        dynamodb,
        AUDIT_TABLE,
        common_table_args(
            AUDIT_TABLE,
            key_schema=[{'AttributeName': 'audit_id', 'KeyType': 'HASH'}],
            attribute_definitions=[
                {'AttributeName': 'audit_id', 'AttributeType': 'S'},
                {'AttributeName': 'user_id', 'AttributeType': 'S'},
                {'AttributeName': 'timestamp', 'AttributeType': 'S'},
                {'AttributeName': 'log_scope', 'AttributeType': 'S'},
            ],
            gsis=[
                {
                    'IndexName': 'user-timestamp-index',
                    'KeySchema': [
                        {'AttributeName': 'user_id', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
                {
                    'IndexName': AUDIT_INDEX,
                    'KeySchema': [
                        {'AttributeName': 'log_scope', 'KeyType': 'HASH'},
                        {'AttributeName': 'timestamp', 'KeyType': 'RANGE'},
                    ],
                    'Projection': {'ProjectionType': 'ALL'},
                },
            ],
        ),
    )


def bootstrap_admin_user(dynamodb):
    """Crea un administrador inicial solo si las variables están presentes."""
    admin_email = os.environ.get('BOOTSTRAP_ADMIN_EMAIL', '').strip().lower()
    admin_password = os.environ.get('BOOTSTRAP_ADMIN_PASSWORD', '').strip()
    admin_name = os.environ.get('BOOTSTRAP_ADMIN_NAME', 'GameVault Admin').strip()
    admin_last_name = os.environ.get('BOOTSTRAP_ADMIN_LAST_NAME', '').strip()

    if not admin_email or not admin_password:
        print("ℹ️ No se creó usuario admin inicial. Define BOOTSTRAP_ADMIN_EMAIL y BOOTSTRAP_ADMIN_PASSWORD si lo necesitas.")
        return

    users_table = dynamodb.Table(USERS_TABLE)
    existing = users_table.query(
        IndexName='email-index',
        KeyConditionExpression=Key('email').eq(admin_email),
        Limit=1,
    ).get('Items', [])

    if existing:
        admin_user = existing[0]
        users_table.update_item(
            Key={'user_id': admin_user['user_id']},
            UpdateExpression='SET #role = :role, updated_at = :updated_at',
            ExpressionAttributeNames={'#role': 'role'},
            ExpressionAttributeValues={':role': 'admin', ':updated_at': now_iso()},
        )
        print(f"✅ Admin existente actualizado: {admin_email}")
        return

    user_id = str(uuid.uuid4())
    timestamp = now_iso()
    users_table.put_item(
        Item={
            'user_id': user_id,
            'email': admin_email,
            'nombre': admin_name,
            'apellido': admin_last_name,
            'prefijo_pais': '',
            'telefono': '',
            'password_hash': generate_password_hash(admin_password),
            'role': 'admin',
            'status': 'active',
            'created_at': timestamp,
            'updated_at': timestamp,
        }
    )
    print(f"✅ Admin inicial creado: {admin_email}")


def main():
    print('🚀 Configurando DynamoDB para GameVault')
    print(f'📍 Región: {DYNAMODB_REGION}')

    dynamodb = boto3.resource('dynamodb', region_name=DYNAMODB_REGION)
    dynamodb_client = boto3.client('dynamodb', region_name=DYNAMODB_REGION)

    create_games_table(dynamodb)
    create_users_table(dynamodb)
    create_reset_table(dynamodb)
    create_audit_table(dynamodb)

    enable_ttl(dynamodb_client, RESET_TABLE, 'ttl')
    enable_ttl(dynamodb_client, AUDIT_TABLE, 'ttl')
    bootstrap_admin_user(dynamodb)

    print('\n🎉 DynamoDB listo para GameVault')
    print(f'   - {GAMES_TABLE}')
    print(f'   - {USERS_TABLE}')
    print(f'   - {RESET_TABLE}')
    print(f'   - {AUDIT_TABLE}')


if __name__ == '__main__':
    main()
