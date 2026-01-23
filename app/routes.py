"""
app/routes.py - Rutas y Controladores de GameVault
Maneja todos los endpoints de la aplicación Flask
"""

import os
import uuid
import io
import base64
from datetime import datetime, timezone
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from botocore.exceptions import ClientError
from flask_mail import Message

from app.models import (
    crear_juego,
    obtener_juegos_por_usuario,
    obtener_juego_por_id,
    eliminar_juego,
    actualizar_juego,
    crear_usuario,
    obtener_usuario_por_email,
    verificar_credenciales,
    validar_email,
    validar_telefono,
    validar_password,
    obtener_todos_usuarios,
    eliminar_usuario,
    actualizar_usuario_nombre,
    # Password Reset
    crear_reset_token,
    validar_reset_token,
    usar_token,
    obtener_usuario_por_email as obtener_usuario,
    # Audit Logs
    crear_log_audit,
    obtener_todos_logs,
    obtener_estadisticas_logs,
    exportar_logs_csv,
    limpiar_logs_antiguos,
    AUDIT_ACTIONS
)


# Crear Blueprint para las rutas principales
main_bp = Blueprint('main', __name__)


# ================================
# CONFIGURACIÓN
# ================================

# User ID por defecto para demo
DEFAULT_USER_ID = 'user-demo-001'

# Configuración S3
S3_BUCKET_NAME = os.environ.get('S3_BUCKET_NAME', 'gamevault-media-files')
S3_REGION = os.environ.get('AWS_REGION', 'us-east-1')


# ================================
# UTILIDADES DE EMAIL
# ================================

def enviar_email_reset_password(destinatario, token):
    """
    Envía un email con el enlace de recuperación de contraseña.
    
    Args:
        destinatario (str): Email del destinatario
        token (str): Token de recuperación
    
    Returns:
        bool: True si se envió, False si hubo error
    """
    try:
        from flask import current_app
        from flask_mail import Message
        
        # Crear el enlace de recuperación usando la nueva ruta
        reset_url = url_for('main.reset_password_with_email', token=token, _external=True)
        
        # Crear el mensaje
        msg = Message(
            subject='Recuperación de Contraseña - GameVault',
            recipients=[destinatario],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #6c5ce7;">🔑 Recuperación de Contraseña</h2>
                <p>Hola,</p>
                <p>Has solicitado recuperar tu contraseña en GameVault. Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                <p style="text-align: center; margin: 30px 0;">
                    <a href="{reset_url}" style="background: #6c5ce7; color: white; padding: 12px 24px; text-decoration: none; border-radius: 8px; display: inline-block;">Recuperar Contraseña</a>
                </p>
                <p>Este enlace expira en 1 hora por seguridad.</p>
                <p>Si no solicitaste este cambio, puedes ignorar este correo.</p>
                <hr>
                <p style="color: #666; font-size: 12px;">GameVault - Tu biblioteca de juegos</p>
            </div>
            """
        )
        
        # Intentar enviar (solo si está configurado)
        mail = current_app.extensions.get('mail')
        if mail:
            mail.send(msg)
            print(f"✅ Email enviado a {destinatario}")
            return True
        else:
            # Modo testing - solo mostrar en consola
            print(f"📧 [MODO TESTING] Email para {destinatario}:")
            print(f"   Enlace: {reset_url}")
            return True
            
    except Exception as e:
        print(f"❌ Error al enviar email: {str(e)}")
        return False


# ================================
# UTILIDADES S3
# ================================

def subir_imagen_a_s3(archivo):
    """
    Sube un archivo de imagen al bucket S3 y retorna la URL pública.
    
    Args:
        archivo: Objeto file de Flask (request.files['imagen'])
    
    Returns:
        str: URL pública del archivo en S3, o None si hay error
    """
    try:
        if archivo is None or archivo.filename == '':
            print("❌ No se proporcionó ningún archivo")
            return None
        
        extension = os.path.splitext(archivo.filename)[1]
        nombre_unico = f"{uuid.uuid4()}{extension}"
        
        import boto3
        s3_client = boto3.client(
            's3',
            region_name=S3_REGION
        )
        
        s3_client.upload_fileobj(
            archivo,
            S3_BUCKET_NAME,
            nombre_unico,
            ExtraArgs={
                'ContentType': archivo.content_type
            }
        )
        
        url_publica = f"https://{S3_BUCKET_NAME}.s3.{S3_REGION}.amazonaws.com/{nombre_unico}"
        
        print(f"✅ Imagen subida exitosamente: {url_publica}")
        return url_publica
        
    except ClientError as e:
        print(f"❌ Error de S3 al subir imagen: {e.response['Error']['Message']}")
        return None
    except Exception as e:
        print(f"❌ Error inesperado al subir imagen: {str(e)}")
        return None


def procesar_imagen_base64(archivo):
    """
    Procesa una imagen y la convierte a base64 (para Demo In-Memory).
    NO sube a S3, procesa todo en memoria.
    
    Args:
        archivo: Objeto file de Flask
    
    Returns:
        str: String base64 de la imagen, o None si hay error
    """
    try:
        if archivo is None or archivo.filename == '':
            print("❌ No se proporcionó ningún archivo")
            return None
        
        # Leer el archivo en memoria
        imagen_bytes = archivo.read()
        
        # Determinar el tipo de contenido
        content_type = archivo.content_type or 'image/jpeg'
        
        # Convertir a base64
        imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        
        # Crear data URL
        data_url = f"data:{content_type};base64,{imagen_base64}"
        
        print(f"✅ Imagen procesada en memoria ({len(imagen_bytes)} bytes)")
        return data_url
        
    except Exception as e:
        print(f"❌ Error al procesar imagen en base64: {str(e)}")
        return None


# ================================
# RUTAS - LANDING PAGE Y DEMO
# ================================

@main_bp.route('/')
def landing():
    """
    Landing Page - Primera impresión de la aplicación.
    Muestra información sobre GameVault y opciones para probar demo o login.
    """
    return render_template('landing.html')


@main_bp.route('/demo', methods=['GET', 'POST'])
def demo():
    """
    Demo In-Memory - Permite probar la app sin subir a S3 ni guardar en BD.
    Procesa imágenes en memoria usando io.BytesIO y base64.
    """
    if request.method == 'POST':
        try:
            titulo = request.form.get('titulo', '').strip()
            imagen = request.files.get('imagen')
            
            if not titulo:
                flash('El título es requerido', 'error')
                return redirect(url_for('main.demo'))
            
            if imagen is None:
                flash('Debes seleccionar una imagen', 'error')
                return redirect(url_for('main.demo'))
            
            # Procesar imagen en memoria (NO subir a S3)
            imagen_base64 = procesar_imagen_base64(imagen)
            
            if imagen_base64 is None:
                flash('Error al procesar la imagen', 'error')
                return redirect(url_for('main.demo'))
            
            # Renderizar resultado directamente (sin guardar en BD)
            return render_template(
                'demo_result.html',
                titulo=titulo,
                imagen_base64=imagen_base64,
                filename=imagen.filename
            )
            
        except Exception as e:
            print(f"❌ Error en demo: {str(e)}")
            flash('Error inesperado al procesar la solicitud', 'error')
            return redirect(url_for('main.demo'))
    
    return render_template('demo_form.html')


# ================================
# RUTAS PRINCIPALES
# ================================

@main_bp.route('/dashboard')
def dashboard():
    """
    Panel principal - Muestra todos los juegos del usuario.
    USA QUERY (eficiente) - NO SCAN.
    Si el usuario está logueado, muestra sus juegos.
    Si no, usa DEFAULT_USER_ID para demo.
    """
    try:
        user_id = session.get('user_id', DEFAULT_USER_ID)
        juegos = obtener_juegos_por_usuario(user_id)
        return render_template('index.html', juegos=juegos)
    except Exception as e:
        print(f"❌ Error en dashboard: {str(e)}")
        flash('Error al cargar los juegos', 'error')
        return render_template('index.html', juegos=[])


@main_bp.route('/agregar', methods=['POST'])
def agregar_juego():
    """
    Ruta para agregar un nuevo juego.
    1. Verifica que el usuario esté autenticado
    2. Recibe los datos del formulario
    3. Sube la imagen a S3
    4. Guarda los datos en DynamoDB
    """
    try:
        if 'user_id' not in session:
            flash('Debes iniciar sesión para agregar juegos', 'error')
            return redirect(url_for('main.dashboard'))
        
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        plataforma = request.form.get('plataforma', 'PC').strip()
        estado = request.form.get('estado', 'N/A').strip()
        imagen = request.files.get('imagen')
        
        if not titulo:
            flash('El título es requerido', 'error')
            return redirect(url_for('main.dashboard'))
        
        if not descripcion:
            flash('La descripción es requerida', 'error')
            return redirect(url_for('main.dashboard'))
        
        if imagen is None:
            flash('Debes subir una imagen', 'error')
            return redirect(url_for('main.dashboard'))
        
        print("📤 Subiendo imagen a S3...")
        imagen_url = subir_imagen_a_s3(imagen)
        
        if imagen_url is None:
            flash('Error al subir la imagen a S3', 'error')
            return redirect(url_for('main.dashboard'))
        
        game_id = str(uuid.uuid4())
        user_id = session['user_id']
        
        print("💾 Guardando juego en DynamoDB...")
        resultado = crear_juego(user_id, game_id, titulo, descripcion, imagen_url, plataforma, estado)
        
        if resultado:
            flash(f'✅ Juego "{titulo}" agregado exitosamente!', 'success')
        else:
            flash('Error al guardar el juego en la base de datos', 'error')
        
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        print(f"❌ Error al agregar juego: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/delete/<game_id>')
def eliminar_juego_ruta(game_id):
    """
    Ruta para eliminar un juego.
    Elimina PRIMERO la imagen de S3, luego el item de DynamoDB.
    Solo elimina juegos del usuario autenticado.
    """
    try:
        if 'user_id' not in session:
            flash('Debes iniciar sesión para eliminar juegos', 'error')
            return redirect(url_for('main.dashboard'))
        
        user_id = session['user_id']
        
        juego = obtener_juego_por_id(user_id, game_id)
        
        if juego is None:
            flash('Juego no encontrado o no tienes permisos', 'error')
            return redirect(url_for('main.dashboard'))
        
        resultado = eliminar_juego(user_id, game_id)
        
        if resultado['success']:
            flash(f'✅ Juego "{juego["titulo"]}" eliminado exitosamente', 'success')
        else:
            flash(f'Error al eliminar el juego: {resultado.get("error", "Error desconocido")}', 'error')
        
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        print(f"❌ Error al eliminar juego: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/edit/<game_id>', methods=['GET', 'POST'])
def editar_juego_ruta(game_id):
    """
    Ruta para editar un juego existente.
    GET: Muestra el formulario de edición con los datos actuales
    POST: Procesa los cambios (título, descripción, y opcionalmente nueva imagen)
    """
    try:
        if 'user_id' not in session:
            flash('Debes iniciar sesión para editar juegos', 'error')
            return redirect(url_for('main.dashboard'))
        
        user_id = session['user_id']
        
        if request.method == 'GET':
            # Obtener datos actuales del juego
            juego = obtener_juego_por_id(user_id, game_id)
            
            if juego is None:
                flash('Juego no encontrado o no tienes permisos', 'error')
                return redirect(url_for('main.dashboard'))
            
            return render_template('edit_game.html', juego=juego)
        
        # POST - Procesar edición
        titulo = request.form.get('titulo', '').strip()
        descripcion = request.form.get('descripcion', '').strip()
        plataforma = request.form.get('plataforma', '').strip()
        estado = request.form.get('estado', '').strip()
        nueva_imagen = request.files.get('nueva_imagen')
        
        if not titulo:
            flash('El título es requerido', 'error')
            return redirect(url_for('main.editar_juego_ruta', game_id=game_id))
        
        nuevos_datos = {
            'titulo': titulo,
            'descripcion': descripcion
        }
        
        # Agregar plataforma y estado si vienen
        if plataforma:
            nuevos_datos['plataforma'] = plataforma
        if estado:
            nuevos_datos['estado'] = estado
        
        resultado = actualizar_juego(user_id, game_id, nuevos_datos, nueva_imagen)
        
        if resultado['success']:
            flash(f'✅ Juego "{titulo}" actualizado exitosamente', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash(f'Error al actualizar el juego: {resultado.get("error", "Error desconocido")}', 'error')
            return redirect(url_for('main.editar_juego_ruta', game_id=game_id))
        
    except Exception as e:
        print(f"❌ Error al editar juego: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/salud')
def salud():
    """Ruta de health check."""
    return {
        'status': 'healthy',
        'app': 'GameVault',
        'user_id': DEFAULT_USER_ID,
        'multi_tenant': True
    }


# ================================
# RUTAS DE AUTENTICACIÓN
# ================================

@main_bp.route('/registro', methods=['GET', 'POST'])
def registro():
    """Ruta para registro de nuevos usuarios."""
    # Si ya está logueado, redirigir al dashboard
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'GET':
        # Mostrar página de registro dedicada
        return render_template('registro.html')
    
    try:
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip().lower()
        prefijo_pais = request.form.get('prefijo_pais', '').strip()
        telefono = request.form.get('telefono', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        errores = []
        
        if not nombre:
            errores.append('El nombre es requerido')
        if not apellido:
            errores.append('Los apellidos son requeridos')
        if not email:
            errores.append('El email es requerido')
        elif not validar_email(email):
            errores.append('El formato del email no es válido')
        if not prefijo_pais:
            errores.append('El prefijo del país es requerido')
        if not telefono:
            errores.append('El número de teléfono es requerido')
        elif not validar_telefono(telefono):
            errores.append('El teléfono debe contener entre 7 y 15 dígitos')
        if not password:
            errores.append('La contraseña es requerida')
        elif not validar_password(password):
            errores.append('La contraseña debe tener al menos 8 caracteres')
        if password != confirm_password:
            errores.append('Las contraseñas no coinciden')
        
        usuario_existente = obtener_usuario_por_email(email)
        if usuario_existente:
            errores.append('El email ya está registrado')
        
        if errores:
            for error in errores:
                flash(error, 'error')
            return redirect(url_for('main.registro'))
        
        password_hash = generate_password_hash(password)
        
        resultado = crear_usuario(nombre, apellido, email, prefijo_pais, telefono, password_hash)
        
        if resultado:
            flash(f'✅ ¡Registro exitoso! Bienvenido {nombre}', 'success')
            session['user_id'] = resultado['user_id']
            session['email'] = email
            session['nombre'] = nombre
            session['role'] = resultado.get('role', 'user')
            
            # Redirigir al panel de admin si es administrador, sino al dashboard
            if session.get('role') == 'admin':
                return redirect(url_for('main.admin_panel'))
            return redirect(url_for('main.dashboard'))
        else:
            flash('Error al registrar el usuario. Intenta nuevamente.', 'error')
            return redirect(url_for('main.registro'))
        
    except Exception as e:
        print(f"❌ Error en registro: {str(e)}")
        flash('Error inesperado al procesar el registro', 'error')
        return redirect(url_for('main.registro'))


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Ruta para inicio de sesión."""
    # Si ya está logueado, redirigir al dashboard
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'GET':
        # Mostrar página de login dedicada
        return render_template('login.html')
    
    # POST - Procesar login
    try:
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()
        
        if not email or not password:
            flash('Email y contraseña son requeridos', 'error')
            return redirect(url_for('main.login'))
        
        usuario = verificar_credenciales(email, password)
        
        if usuario is None:
            # Log de login fallido
            crear_log_audit(
                user_id='unknown',
                action='FAILED_LOGIN',
                resource='auth',
                details={'email': email, 'reason': 'user_not_found'},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='FAILED'
            )
            flash('Email o contraseña incorrectos', 'error')
            return redirect(url_for('main.login'))
        
        if not check_password_hash(usuario['password_hash'], password):
            # Log de login fallido (contraseña incorrecta)
            crear_log_audit(
                user_id=usuario['user_id'],
                action='FAILED_LOGIN',
                resource='auth',
                details={'email': email, 'reason': 'wrong_password'},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='FAILED'
            )
            flash('Email o contraseña incorrectos', 'error')
            return redirect(url_for('main.login'))
        
        session['user_id'] = usuario['user_id']
        session['email'] = usuario['email']
        session['nombre'] = usuario['nombre']
        session['role'] = usuario.get('role', 'user')  # Guardar rol en sesión
        
        # Log de login exitoso
        crear_log_audit(
            user_id=usuario['user_id'],
            action='LOGIN',
            resource='auth',
            details={'email': email},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='SUCCESS'
        )
        
        flash(f'¡Bienvenido de nuevo, {usuario["nombre"]}!', 'success')
        
        # Redirigir al panel de admin si es administrador, sino al dashboard
        if session.get('role') == 'admin':
            return redirect(url_for('main.admin_panel'))
        return redirect(url_for('main.dashboard'))
        
    except Exception as e:
        print(f"❌ Error en login: {str(e)}")
        flash('Error inesperado al iniciar sesión', 'error')
        return redirect(url_for('main.login'))


@main_bp.route('/logout')
def logout():
    """Ruta para cerrar sesión."""
    try:
        nombre = session.get('nombre', 'Usuario')
        session.clear()
        flash(f'¡Hasta luego, {nombre}!', 'success')
    except Exception as e:
        flash('Error al cerrar sesión', 'error')
    
    return redirect(url_for('main.landing'))


# ================================
# RUTAS DE ADMINISTRACIÓN
# ================================

@main_bp.route('/admin')
def admin_panel():
    """
    Panel de Administración - Solo para administradores.
    Lista todos los usuarios registrados.
    """
    # Verificar que el usuario está autenticado y es admin
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder al panel de administración', 'error')
        return redirect(url_for('main.login'))
    
    if session.get('role') != 'admin':
        flash('🚫 Acceso denegado. Solo los administradores pueden acceder a esta sección.', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        usuarios = obtener_todos_usuarios()
        return render_template('admin.html', usuarios=usuarios)
    except Exception as e:
        print(f"❌ Error en panel de admin: {str(e)}")
        flash('Error al cargar los usuarios', 'error')
        return redirect(url_for('main.dashboard'))


@main_bp.route('/admin/delete/<user_id>', methods=['POST'])
def admin_eliminar_usuario(user_id):
    """
    Elimina un usuario (solo para administradores).
    No permite eliminarse a sí mismo.
    """
    # Verificar que el usuario es admin
    if session.get('role') != 'admin':
        flash('🚫 Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    # No permitir eliminarse a sí mismo
    if session.get('user_id') == user_id:
        flash('⚠️ No puedes eliminar tu propia cuenta desde el panel de administración', 'error')
        return redirect(url_for('main.admin_panel'))
    
    try:
        resultado = eliminar_usuario(user_id)
        
        if resultado['success']:
            flash('✅ Usuario eliminado exitosamente', 'success')
        else:
            flash(f'Error al eliminar usuario: {resultado.get("error", "Error desconocido")}', 'error')
        
        return redirect(url_for('main.admin_panel'))
        
    except Exception as e:
        print(f"❌ Error al eliminar usuario: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return redirect(url_for('main.admin_panel'))


@main_bp.route('/admin/edit/<user_id>', methods=['POST'])
def admin_editar_usuario(user_id):
    """
    Edita el nombre de un usuario (solo para administradores).
    """
    # Verificar que el usuario es admin
    if session.get('role') != 'admin':
        flash('🚫 Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        nuevo_nombre = request.form.get('nombre', '').strip()
        
        if not nuevo_nombre:
            flash('El nombre no puede estar vacío', 'error')
            return redirect(url_for('main.admin_panel'))
        
        resultado = actualizar_usuario_nombre(user_id, nuevo_nombre)
        
        if resultado['success']:
            # Log de actualización de usuario
            crear_log_audit(
                user_id=session.get('user_id', 'admin'),
                action='ADMIN_ACTION',
                resource='users',
                details={'target_user_id': user_id, 'action': 'update_name', 'new_name': nuevo_nombre},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='SUCCESS'
            )
            flash('✅ Nombre actualizado exitosamente', 'success')
        else:
            flash(f'Error al actualizar nombre: {resultado.get("error", "Error desconocido")}', 'error')
        
        return redirect(url_for('main.admin_panel'))
        
    except Exception as e:
        print(f"❌ Error al editar usuario: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return redirect(url_for('main.admin_panel'))


# ================================
# RUTAS DE RECUPERACIÓN DE CONTRASEÑA
# ================================

@main_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """
    Ruta para solicitar recuperación de contraseña.
    GET: Muestra formulario de solicitud
    POST: Procesa el email y envía link de reset
    """
    # Si ya está logueado, redirigir al dashboard
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    
    if request.method == 'GET':
        return render_template('forgot_password.html')
    
    try:
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('El email es requerido', 'error')
            return redirect(url_for('main.forgot_password'))
        
        # Verificar si el usuario existe
        usuario = obtener_usuario(email)
        
        # ALWAYS show the same message (security best practice)
        # Don't reveal if email exists or not
        flash('Si el email está registrado, recibirás un enlace para recuperar tu contraseña.', 'success')
        
        if usuario:
            # Crear token de recuperación
            ip_address = request.remote_addr or 'unknown'
            result = crear_reset_token(usuario['user_id'], ip_address)
            
            if result['success']:
                # Enviar email con el enlace de recuperación
                enviar_email_reset_password(email, result['token'])
                
                # Log de solicitud de recuperación
                crear_log_audit(
                    user_id=usuario['user_id'],
                    action='PASSWORD_RESET_REQUEST',
                    resource='auth',
                    details={'email': email, 'method': 'forgot_password'},
                    ip_address=ip_address,
                    user_agent=request.headers.get('User-Agent', 'unknown'),
                    status='SUCCESS'
                )
                
                # Mostrar token siempre (para recuperación sin email)
                flash(f'Token de recuperación: {result["token"]}', 'info')
                print(f"🔑 Token de reset para {email}: {result['token']}")
            else:
                flash('Error al crear el token de recuperación', 'error')
        
        return redirect(url_for('main.forgot_password'))
        
    except Exception as e:
        print(f"❌ Error en forgot_password: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return redirect(url_for('main.forgot_password'))


@main_bp.route('/validate-token')
def validate_token_page():
    """
    Página para que el usuario pegue su token de recuperación.
    """
    # Si ya está logueado, redirigir al dashboard
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    
    return render_template('validate_token.html')


@main_bp.route('/verify-token', methods=['POST'])
def verify_token():
    """
    Valida el token y redirige a la página de reset con email.
    """
    # Si ya está logueado, redirigir al dashboard
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    
    try:
        token = request.form.get('token', '').strip()
        
        if not token:
            flash('El token es requerido', 'error')
            return redirect(url_for('main.validate_token_page'))
        
        # Validar el token
        token_validation = validar_reset_token(token)
        
        if not token_validation['valid']:
            flash(token_validation['error'], 'error')
            return redirect(url_for('main.validate_token_page'))
        
        # Token válido - obtener el email del usuario
        user_id = token_validation['user_id']
        usuario = obtener_usuario_por_id_func(user_id)
        
        if usuario is None:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('main.validate_token_page'))
        
        # Redirigir a la página de reset con el email
        email = usuario.get('email', '')
        return redirect(url_for('main.reset_password_with_email', token=token, email=email))
        
    except Exception as e:
        print(f"❌ Error en verify_token: {str(e)}")
        flash('Error inesperado al validar el token', 'error')
        return redirect(url_for('main.validate_token_page'))


@main_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password_with_email(token):
    """
    Ruta para establecer nueva contraseña con token válido y email.
    GET: Muestra formulario de nueva contraseña con email deshabilitado
    POST: Procesa el cambio de contraseña
    """
    # Si ya está logueado, redirigir al dashboard
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    
    # Validar token
    token_validation = validar_reset_token(token)
    
    if not token_validation['valid']:
        flash(token_validation['error'], 'error')
        return redirect(url_for('main.forgot_password'))
    
    # Obtener email de los parámetros o del token
    email = request.args.get('email', '')
    if not email:
        user_id = token_validation['user_id']
        usuario = obtener_usuario_por_id_func(user_id)
        email = usuario.get('email', '') if usuario else ''
    
    if request.method == 'GET':
        return render_template('reset_password.html', token=token, email=email)
    
    # POST - Procesar cambio de contraseña
    try:
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()
        
        errores = []
        
        if not password:
            errores.append('La contraseña es requerida')
        elif not validar_password(password):
            errores.append('La contraseña debe tener al menos 8 caracteres')
        if password != confirm_password:
            errores.append('Las contraseñas no coinciden')
        
        if errores:
            for error in errores:
                flash(error, 'error')
            return render_template('reset_password.html', token=token, email=email)
        
        # Actualizar contraseña del usuario
        user_id = token_validation['user_id']
        usuario = obtener_usuario_por_id_func(user_id)
        
        if usuario is None:
            flash('Usuario no encontrado', 'error')
            return redirect(url_for('main.forgot_password'))
        
        # Actualizar contraseña
        from werkzeug.security import generate_password_hash
        nueva_contrasena_hash = generate_password_hash(password)
        
        resultado = actualizar_password_usuario(user_id, nueva_contrasena_hash)
        
        if resultado['success']:
            # Marcar token como usado
            usar_token(token)
            
            # Log del cambio de contraseña
            crear_log_audit(
                user_id=user_id,
                action='PASSWORD_RESET',
                resource='auth',
                details={'status': 'password_changed'},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='SUCCESS'
            )
            
            flash('✅ Tu contraseña ha sido actualizada exitosamente. Ahora puedes iniciar sesión.', 'success')
            return redirect(url_for('main.login'))
        else:
            flash(f'Error al actualizar contraseña: {resultado.get("error", "Error desconocido")}', 'error')
            return render_template('reset_password.html', token=token, email=email)
        
    except Exception as e:
        print(f"❌ Error en reset_password: {str(e)}")
        flash('Error inesperado al procesar la solicitud', 'error')
        return render_template('reset_password.html', token=token, email=email)


# ================================
# RUTAS DE ADMIN - LOGS DE ACTIVIDAD
# ================================

@main_bp.route('/admin/logs')
def admin_logs():
    """
    Panel de Logs de Actividad - Solo para administradores.
    Muestra todos los logs de auditoría con filtros.
    """
    # Verificar que el usuario está autenticado y es admin
    if 'user_id' not in session:
        flash('Debes iniciar sesión para acceder', 'error')
        return redirect(url_for('main.login'))
    
    if session.get('role') != 'admin':
        flash('🚫 Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Obtener filtros de la URL
        filters = {}
        
        if request.args.get('user_id'):
            filters['user_id'] = request.args.get('user_id')
        
        if request.args.get('action'):
            filters['action'] = request.args.get('action')
        
        if request.args.get('status'):
            filters['status'] = request.args.get('status')
        
        if request.args.get('start_date'):
            filters['start_date'] = request.args.get('start_date')
        
        if request.args.get('end_date'):
            filters['end_date'] = request.args.get('end_date')
        
        # Obtener logs
        logs = obtener_todos_logs(filters, limit=100)
        
        # Obtener estadísticas
        stats = obtener_estadisticas_logs()
        
        return render_template('admin_logs.html', logs=logs, stats=stats, filters=filters, AUDIT_ACTIONS=AUDIT_ACTIONS)
        
    except Exception as e:
        print(f"❌ Error en admin_logs: {str(e)}")
        flash('Error al cargar los logs', 'error')
        return redirect(url_for('main.admin_panel'))


@main_bp.route('/admin/logs/export')
def admin_logs_export():
    """
    Exporta los logs de auditoría a CSV.
    """
    # Verificar que el usuario es admin
    if session.get('role') != 'admin':
        flash('🚫 Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Obtener filtros
        filters = {}
        
        if request.args.get('user_id'):
            filters['user_id'] = request.args.get('user_id')
        
        if request.args.get('action'):
            filters['action'] = request.args.get('action')
        
        # Obtener logs
        logs = obtener_todos_logs(filters, limit=1000)
        
        # Exportar a CSV
        csv_content = exportar_logs_csv(logs)
        
        # Crear respuesta
        from flask import Response
        
        response = Response(csv_content, mimetype='text/csv')
        response.headers.set('Content-Disposition', 'attachment', filename='audit_logs.csv')
        
        return response
        
    except Exception as e:
        print(f"❌ Error al exportar logs: {str(e)}")
        flash('Error al exportar logs', 'error')
        return redirect(url_for('main.admin_logs'))


@main_bp.route('/admin/logs/clear', methods=['POST'])
def admin_logs_clear():
    """
    Elimina los logs de auditoría antiguos para liberar espacio.
    Solo para administradores.
    """
    # Verificar que el usuario es admin
    if session.get('role') != 'admin':
        flash('🚫 Acceso denegado', 'error')
        return redirect(url_for('main.dashboard'))
    
    try:
        # Obtener días a retener (por defecto 7 días)
        dias = int(request.form.get('dias', 7))
        
        if dias < 1:
            dias = 1
        
        # Limpiar logs antiguos
        resultado = limpiar_logs_antiguos(dias)
        
        if resultado.get('deleted', 0) > 0:
            # Log de la limpieza
            crear_log_audit(
                user_id=session.get('user_id', 'admin'),
                action='ADMIN_ACTION',
                resource='audit_logs',
                details={'action': 'clear_logs', 'deleted_count': resultado['deleted'], 'retention_days': dias},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='SUCCESS'
            )
            flash(f'✅ Se eliminaron {resultado["deleted"]} logs antiguos (mayores a {dias} días)', 'success')
        else:
            flash('✅ No hay logs antiguos para eliminar', 'success')
        
        return redirect(url_for('main.admin_logs'))
        
    except Exception as e:
        print(f"❌ Error al limpiar logs: {str(e)}")
        flash('Error al limpiar logs', 'error')
        return redirect(url_for('main.admin_logs'))


# ================================
# FUNCIONES AUXILIARES
# ================================

def obtener_usuario_por_id_func(user_id):
    """Obtiene un usuario por su ID."""
    try:
        tabla = get_dynamodb_users_table()
        response = tabla.get_item(Key={'user_id': user_id})
        return response.get('Item')
    except Exception as e:
        print(f"❌ Error al obtener usuario por ID: {str(e)}")
        return None


def actualizar_password_usuario(user_id, password_hash):
    """Actualiza la contraseña de un usuario."""
    try:
        tabla = get_dynamodb_users_table()
        
        response = tabla.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET password_hash = :password_hash, updated_at = :updated_at',
            ExpressionAttributeValues={
                ':password_hash': password_hash,
                ':updated_at': datetime.now(timezone.utc).isoformat()
            },
            ReturnValues='ALL_NEW'
        )
        
        print(f"✅ Contraseña actualizada para usuario {user_id}")
        return {'success': True, 'error': None}
        
    except ClientError as e:
        print(f"❌ Error de DynamoDB al actualizar contraseña: {e.response['Error']['Message']}")
        return {'success': False, 'error': e.response['Error']['Message']}
    except Exception as e:
        print(f"❌ Error inesperado al actualizar contraseña: {str(e)}")
        return {'success': False, 'error': str(e)}


def get_dynamodb_users_table():
    """Obtiene la tabla de usuarios."""
    import boto3
    import os
    dynamodb = boto3.resource(
        'dynamodb',
        region_name=os.environ.get('AWS_REGION', 'us-east-1')
    )
    return dynamodb.Table(os.environ.get('DYNAMODB_USERS_TABLE', 'GameVaultUsers'))

