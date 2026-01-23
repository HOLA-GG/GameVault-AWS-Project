#!/usr/bin/env python3
"""
Script de Setup para S3 - GameVault
Crea y configura el bucket S3 para almacenar imágenes de juegos.
"""

import boto3
from botocore.exceptions import ClientError

# Configuración según app.py
S3_BUCKET_NAME = 'gamevault-media-files'
S3_REGION = 'us-east-1'


def crear_bucket_s3(s3_client, bucket_name, region):
    """Crea el bucket S3 si no existe."""
    try:
        # Verificar si el bucket ya existe
        s3_client.head_bucket(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' ya existe")
        return True
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        
        if error_code == '404':
            # El bucket no existe, crearlo
            try:
                if region == 'us-east-1':
                    # us-east-1 no requiere LocationConstraint
                    s3_client.create_bucket(Bucket=bucket_name)
                else:
                    s3_client.create_bucket(
                        Bucket=bucket_name,
                        CreateBucketConfiguration={
                            'LocationConstraint': region
                        }
                    )
                print(f"⏳ Creando bucket '{bucket_name}'...")
                # Esperar a que el bucket exista
                waiter = s3_client.get_waiter('bucket_exists')
                waiter.wait(Bucket=bucket_name)
                print(f"✅ Bucket '{bucket_name}' creado exitosamente!")
                return True
            except ClientError as create_error:
                print(f"❌ Error al crear bucket: {create_error.response['Error']['Message']}")
                return False
        else:
            print(f"❌ Error al verificar bucket: {e.response['Error']['Message']}")
            return False


def configurar_cors(s3_client, bucket_name):
    """Configura CORS para permitir uploads desde la aplicación web."""
    cors_configuration = {
        'CORSRules': [
            {
                'AllowedHeaders': ['*'],
                'AllowedMethods': ['GET', 'PUT', 'POST', 'DELETE', 'HEAD'],
                'AllowedOrigins': ['*'],  # En producción, especificar tu dominio
                'ExposeHeaders': ['ETag'],
                'MaxAgeSeconds': 3000
            }
        ]
    }
    
    try:
        s3_client.put_bucket_cors(
            Bucket=bucket_name,
            CORSConfiguration=cors_configuration
        )
        print("✅ CORS configurado correctamente")
        return True
    except ClientError as e:
        print(f"⚠️ Error al configurar CORS: {e.response['Error']['Message']}")
        return False


def configurar_policy(s3_client, bucket_name):
    """Configura la política del bucket para acceso público de lectura."""
    # Nota: En producción, considera usar CloudFront para servir imágenes
    # y mantener el bucket privado
    policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Sid": "PublicReadGetObject",
                "Effect": "Allow",
                "Principal": "*",
                "Action": "s3:GetObject",
                "Resource": f"arn:aws:s3:::{bucket_name}/*"
            }
        ]
    }
    
    try:
        s3_client.put_bucket_policy(
            Bucket=bucket_name,
            Policy=json.dumps(policy)
        )
        print("✅ Política del bucket configurada (lectura pública)")
        return True
    except ClientError as e:
        print(f"⚠️ Error al configurar política: {e.response['Error']['Message']}")
        return False


def configurar_block_public_access(s3_client, bucket_name):
    """Desbloquea el acceso público para permitir lectura de objetos."""
    try:
        # Desactivar block public access
        s3_client.put_public_access_block(
            Bucket=bucket_name,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        print("✅ Block Public Access configurado correctamente")
        return True
    except ClientError as e:
        print(f"⚠️ Error al configurar block public access: {e.response['Error']['Message']}")
        return False


def habilitar_versioning(s3_client, bucket_name):
    """Habilita el versionado del bucket para mantener historial de objetos."""
    try:
        s3_client.put_bucket_versioning(
            Bucket=bucket_name,
            VersioningConfiguration={
                'Status': 'Enabled'
            }
        )
        print("✅ Versioning habilitado correctamente")
        return True
    except ClientError as e:
        print(f"⚠️ Error al habilitar versioning: {e.response['Error']['Message']}")
        return False


def verificar_bucket(s3_client, bucket_name):
    """Verifica información del bucket."""
    try:
        # Obtener ubicación del bucket
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        region = response.get('LocationConstraint', 'us-east-1')
        print(f"📍 Región del bucket: {region}")
        
        # Obtener ACL del bucket
        acl_response = s3_client.get_bucket_acl(Bucket=bucket_name)
        print(f"✅ Bucket '{bucket_name}' verificado exitosamente")
        return True
    except ClientError as e:
        print(f"❌ Error al verificar bucket: {e.response['Error']['Message']}")
        return False


def main():
    print("🚀 Configurando S3 para GameVault...")
    print(f"📍 Bucket: {S3_BUCKET_NAME}")
    print(f"📍 Región: {S3_REGION}")
    
    # Inicializar cliente S3
    s3_client = boto3.client('s3', region_name=S3_REGION)
    
    # Paso 1: Crear bucket
    if not crear_bucket_s3(s3_client, S3_BUCKET_NAME, S3_REGION):
        print("❌ Error al crear bucket. Abortando...")
        return
    
    # Paso 2: Configurar Block Public Access
    configurar_block_public_access(s3_client, S3_BUCKET_NAME)
    
    # Paso 3: Configurar política (lectura pública)
    configurar_policy(s3_client, S3_BUCKET_NAME)
    
    # Paso 4: Configurar CORS
    configurar_cors(s3_client, S3_BUCKET_NAME)
    
    # Paso 5: Habilitar versioning
    habilitar_versioning(s3_client, S3_BUCKET_NAME)
    
    # Paso 6: Verificar bucket
    verificar_bucket(s3_client, S3_BUCKET_NAME)
    
    print("\n🎉 Configuración de S3 completada!")
    print(f"\n📝 Próximos pasos:")
    print(f"  1. Sube imágenes usando la función subir_imagen_a_s3() en app.py")
    print(f"  2. Las imágenes estarán disponibles en: https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/")
    print(f"  3. Considera usar CloudFront para mejor rendimiento")


if __name__ == '__main__':
    import json
    main()

