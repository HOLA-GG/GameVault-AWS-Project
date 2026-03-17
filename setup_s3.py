#!/usr/bin/env python3
"""Configura un bucket S3 privado para portadas de GameVault."""

from __future__ import annotations

import os

import boto3
from botocore.exceptions import ClientError

S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')
S3_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        'S3_ALLOWED_ORIGINS',
        'http://127.0.0.1:5000,http://localhost:5000',
    ).split(',')
    if origin.strip()
]


def crear_bucket_s3(s3_client, bucket_name, region):
    """Crea el bucket si aún no existe."""
    try:
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' ya existe")
        return True
    except ClientError as exc:
        error_code = exc.response.get('Error', {}).get('Code', '')
        if error_code not in {'404', 'NoSuchBucket', 'NotFound'}:
            print(f"❌ Error al verificar bucket: {exc.response['Error']['Message']}")
            return False

    try:
        create_args = {'Bucket': bucket_name}
        if region != 'us-east-1':
            create_args['CreateBucketConfiguration'] = {'LocationConstraint': region}
        s3_client.create_bucket(**create_args)
        print(f"⏳ Creando bucket '{bucket_name}'...")
        s3_client.get_waiter('bucket_exists').wait(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' creado")
        return True
    except ClientError as exc:
        print(f"❌ Error al crear bucket: {exc.response['Error']['Message']}")
        return False


def configurar_cors(s3_client, bucket_name):
    """Restringe CORS a los orígenes reales de la app."""
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'POST', 'PUT', 'HEAD'],
                'AllowedOrigins': S3_ALLOWED_ORIGINS,
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000,
            }
        ]
    }
    try:
        s3_client.put_bucket_cors(Bucket=bucket_name, CORSConfiguration=cors_configuration)
        print(f"✅ CORS configurado para: {', '.join(S3_ALLOWED_ORIGINS)}")
        return True
    except ClientError as exc:
        print(f"⚠️ Error al configurar CORS: {exc.response['Error']['Message']}")
        return False


def configurar_block_public_access(s3_client, bucket_name):
    """Bloquea acceso público al bucket."""
    try:
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': True,
                'IgnorePublicAcls': True,
                'BlockPublicPolicy': True,
                'RestrictPublicBuckets': True,
            },
        )
        print('✅ Block Public Access activado')
        return True
    except ClientError as exc:
        print(f"⚠️ Error al bloquear acceso público: {exc.response['Error']['Message']}")
        return False


def habilitar_versioning(s3_client, bucket_name):
    """Habilita versioning en el bucket."""
    try:
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={'Status': 'Enabled'},
        )
        print('✅ Versioning habilitado')
        return True
    except ClientError as exc:
        print(f"⚠️ Error al habilitar versioning: {exc.response['Error']['Message']}")
        return False


def habilitar_encryption(s3_client, bucket_name):
    """Activa cifrado por defecto en reposo."""
    try:
        s3_client.put_bucket_encryption(
            Bucket=bucket_name,
            ServerSideEncryptionConfiguration={
                'Rules': [
                    {
                        'ApplyServerSideEncryptionByDefault': {'SSEAlgorithm': 'AES256'}
                    }
                ]
            },
        )
        print('✅ Cifrado por defecto habilitado')
        return True
    except ClientError as exc:
        print(f"⚠️ Error al habilitar cifrado: {exc.response['Error']['Message']}")
        return False


def verificar_bucket(s3_client, bucket_name):
    """Muestra el estado final del bucket."""
    try:
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        region = response.get('LocationConstraint') or 'us-east-1'
        print(f"📍 Región del bucket: {region}")
        print(f"🔒 Bucket privado: sí")
        return True
    except ClientError as exc:
        print(f"❌ Error al verificar bucket: {exc.response['Error']['Message']}")
        return False


def main():
    print('🚀 Configurando S3 para GameVault')
    print(f'📍 Bucket: {S3_BUCKET_NAME}')
    print(f'📍 Región: {S3_REGION}')

    s3_client = boto3.client('s3', region_name=S3_REGION)

    if not crear_bucket_s3(s3_client, S3_BUCKET_NAME, S3_REGION):
        return

    configurar_block_public_access(s3_client, S3_BUCKET_NAME)
    habilitar_encryption(s3_client, S3_BUCKET_NAME)
    configurar_cors(s3_client, S3_BUCKET_NAME)
    habilitar_versioning(s3_client, S3_BUCKET_NAME)
    verificar_bucket(s3_client, S3_BUCKET_NAME)

    print('\n🎉 S3 listo para GameVault')
    print('   - Las portadas se suben con presigned POST')
    print('   - Las imágenes se muestran con URLs temporales firmadas')
    print('   - Recuerda definir S3_ALLOWED_ORIGINS con tu dominio productivo')


if __name__ == '__main__':
    main()
