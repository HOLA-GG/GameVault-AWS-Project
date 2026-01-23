#!/usr/bin/env python3
"""
run.py - Punto de Entrada de GameVault
Ejecuta la aplicación Flask con configuración multi-tenant para AWS EC2
"""

from app import app

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 INICIANDO GAMEVAULT MULTI-TENANT EN AWS EC2")
    print("=" * 60)
    print(f"📍 Tabla DynamoDB Games: {app.config.get('DYNAMODB_TABLE', 'GameVault')}")
    print(f"📍 Tabla DynamoDB Users: {app.config.get('DYNAMODB_USERS_TABLE', 'GameVaultUsers')}")
    print(f"📍 Bucket S3: {app.config.get('S3_BUCKET_NAME', 'gamevault-media-files')}")
    print(f"📍 Región AWS: {app.config.get('S3_REGION', 'us-east-1')}")
    print(f"📍 User ID Demo: {app.config.get('DEFAULT_USER_ID', 'user-demo-001')}")
    print("=" * 60)
    print("📝 Rutas disponibles:")
    print("   • /         → Landing Page")
    print("   • /demo     → Demo In-Memory (sin BD)")
    print("   • /dashboard→ Panel Principal")
    print("   • /agregar  → Agregar juego")
    print("   • /delete/<id> → Eliminar juego")
    print("   • /edit/<id> → Editar juego")
    print("   • /registro → Registrarse")
    print("   • /login    → Iniciar sesión")
    print("   • /logout   → Cerrar sesión")
    print("=" * 60)
    
    # ⚠️ IMPORTANTE: host='0.0.0.0' es obligatorio en la nube.
    app.run(
        host='0.0.0.0',  # Escuchar en todas las interfaces
        port=5000,
        debug=True  # Activar debug en desarrollo
    )

