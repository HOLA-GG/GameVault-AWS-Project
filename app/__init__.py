"""
app/__init__.py - Application Factory Pattern para GameVault
Inicializa la aplicación Flask de forma modular
"""

import os
from flask import Flask
from flask_mail import Mail


# Configuración de Email (Gmail SMTP)
def get_email_config():
    """Configuración de email desde variables de entorno."""
    return {
        'MAIL_SERVER': os.environ.get('MAIL_SERVER', 'smtp.gmail.com'),
        'MAIL_PORT': int(os.environ.get('MAIL_PORT', 587)),
        'MAIL_USE_TLS': os.environ.get('MAIL_USE_TLS', 'true').lower() == 'true',
        'MAIL_USERNAME': os.environ.get('MAIL_USERNAME', ''),
        'MAIL_PASSWORD': os.environ.get('MAIL_PASSWORD', ''),
        'MAIL_DEFAULT_SENDER': os.environ.get('MAIL_DEFAULT_SENDER', 'GameVault <noreply@gamevault.com>')
    }


def create_app():
    """
    Crea y configura la aplicación Flask.
    Usa Application Factory Pattern para mejor modularidad.
    
    Returns:
        Flask: Instancia configurada de la aplicación
    """
    app = Flask(__name__)
    
    # Configuración de la aplicación
    app.secret_key = os.environ.get('SECRET_KEY', 'gamevault-secret-key-change-in-production')
    
    # Configuración Multi-Tenant
    app.config['DEFAULT_USER_ID'] = os.environ.get('DEFAULT_USER_ID', 'user-demo-001')
    
    # Configuración de AWS S3
    app.config['S3_BUCKET_NAME'] = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
    app.config['S3_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Configuración de DynamoDB
    app.config['DYNAMODB_TABLE'] = os.environ.get('DYNAMODB_TABLE', 'GameVault')
    app.config['DYNAMODB_USERS_TABLE'] = os.environ.get('DYNAMODB_USERS_TABLE', 'GameVaultUsers')
    app.config['DYNAMODB_REGION'] = os.environ.get('AWS_REGION', 'us-east-1')
    
    # Configuración de Email
    email_config = get_email_config()
    app.config.update(email_config)
    
    # Inicializar Flask-Mail
    mail = Mail(app)
    
    # Registrar Blueprints (rutas)
    from app.routes import main_bp
    
    app.register_blueprint(main_bp, url_prefix='/')
    
    return app


# Crear instancia de la aplicación para uso en run.py
app = create_app()

