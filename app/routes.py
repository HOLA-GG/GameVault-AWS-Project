"""Rutas principales y controladores de GameVault."""

from __future__ import annotations

import base64
import hashlib
import math
import os
import uuid
from collections import Counter
from datetime import datetime, timedelta, timezone
from functools import wraps
from urllib.parse import unquote, urljoin, urlparse

from flask import (
    Blueprint,
    Response,
    current_app,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_mail import Message
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from app.extensions import csrf, limiter, mail
from app.models import (
    AUDIT_ACTIONS,
    aplicar_ratings_showcase,
    as_iso,
    actualizar_juego,
    actualizar_password_usuario,
    actualizar_usuario_nombre,
    actualizar_usuario_perfil,
    combinar_rating_showcase,
    contar_resumenes_colecciones,
    obtener_colecciones_publicas,
    obtener_resumenes_colecciones,
    registrar_rating_showcase,
    crear_juego,
    crear_log_audit,
    crear_presigned_upload,
    crear_reset_token,
    contar_usuarios,
    crear_url_firmada_lectura,
    crear_usuario,
    database_healthcheck,
    eliminar_juego,
    eliminar_usuario,
    exportar_logs_csv,
    limpiar_logs_antiguos,
    obtener_estadisticas_logs,
    obtener_juego_por_id,
    obtener_juegos_por_usuario,
    obtener_logs_por_usuario,
    obtener_todos_logs,
    obtener_todos_usuarios,
    obtener_usuario_por_email,
    obtener_usuario_por_id,
    obtener_usuarios_por_ids,
    usar_token,
    validar_email,
    validar_password,
    validar_reset_token,
    validar_telefono,
    verificar_credenciales,
)


main_bp = Blueprint('main', __name__)

ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}
GAME_PLATFORM_OPTIONS = ['PC', 'PlayStation', 'Xbox', 'Nintendo', 'Mobile', 'Otro']
GAME_CONDITION_OPTIONS = ['N/A', 'Nuevo', 'Como Nuevo', 'Bueno', 'Regular']
GAME_CATEGORY_OPTIONS = ['Biblioteca', 'Jugando', 'Backlog', 'Completado', 'Wishlist']
GAME_PRIORITY_OPTIONS = ['Baja', 'Media', 'Alta']
GAME_RATING_OPTIONS = list(range(1, 11))

ACTION_BADGE_GROUPS = {
    'action-auth': {'LOGIN', 'LOGOUT', 'FAILED_LOGIN', 'PASSWORD_RESET_REQUEST', 'PASSWORD_RESET', 'CHANGE_PASSWORD'},
    'action-games': {'CREATE_GAME', 'UPDATE_GAME', 'DELETE_GAME'},
    'action-users': {'REGISTER', 'UPDATE_PROFILE'},
    'action-admin': {'ADMIN_ACTION'},
}

# Pre-calculated reverse mapping for O(1) badge class lookup.
_ACTION_BADGE_MAP = {
    action: class_name
    for class_name, actions in ACTION_BADGE_GROUPS.items()
    for action in actions
}

LANDING_SAMPLE_COLLECTIONS = [
    {
        'id': 'demo-nintendo-reliquias',
        'title': 'Nintendo reliquias',
        'owner_name': 'Colección Demo',
        'summary': 'Game Boy, SNES, N64 y ediciones con caja bien conservada.',
        'total_games': 42,
        'favorites_count': 12,
        'average_rating': 4.5,
        'base_votes_count': 18,
        'dominant_platform': 'Nintendo',
    },
    {
        'id': 'demo-jrpg-esenciales',
        'title': 'JRPG esenciales',
        'owner_name': 'Colección Demo',
        'summary': 'Una selección orientada a saga, completismo y estado del empaque.',
        'total_games': 29,
        'favorites_count': 9,
        'average_rating': 4.0,
        'base_votes_count': 11,
        'dominant_platform': 'PlayStation',
    },
    {
        'id': 'demo-indies-vitrina',
        'title': 'Indies de vitrina',
        'owner_name': 'Colección Demo',
        'summary': 'Colección pensada para descubrir indies físicos y sus ediciones especiales.',
        'total_games': 18,
        'favorites_count': 7,
        'average_rating': 5.0,
        'base_votes_count': 6,
        'dominant_platform': 'Switch',
    },
]


def require_login(view):
    """Protege rutas que requieren autenticación con validación en tiempo real."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            flash('Debes iniciar sesión para acceder a esta sección.', 'error')
            return redirect(url_for('main.login', next=request.full_path.rstrip('?')))

        # Real-time database validation to prevent stale sessions (Security enhancement)
        user = obtener_usuario_por_id(user_id)
        if not user or user.get('status') != 'active':
            session.clear()
            flash('Tu sesión ha expirado o tu cuenta no está activa.', 'error')
            return redirect(url_for('main.login'))

        # Global session invalidation on password change (Security enhancement)
        # We store a SHA256 of the password hash in the session to detect changes.
        current_pw_hash_gen = hashlib.sha256(user['password_hash'].encode('utf-8')).hexdigest()
        if session.get('_pw_hash') != current_pw_hash_gen:
            session.clear()
            flash('Tu sesión ha sido invalidada por un cambio de seguridad. Inicia sesión de nuevo.', 'error')
            return redirect(url_for('main.login'))

        g.current_user = user
        return view(*args, **kwargs)

    return wrapped


def require_admin(view):
    """Protege rutas de administración con validación en tiempo real."""

    @wraps(view)
    @require_login
    def wrapped(*args, **kwargs):
        # Use g.current_user cached by require_login to avoid redundant DB queries
        user = getattr(g, 'current_user', None)
        if not user:
            user = obtener_usuario_por_id(session.get('user_id'))

        if not user or user.get('role') != 'admin':
            flash('Acceso denegado. Solo administradores.', 'error')
            return redirect(url_for('main.dashboard'))
        return view(*args, **kwargs)

    return wrapped


def is_valid_image_file(file_storage) -> tuple[bool, str | None]:
    """Valida extensión y MIME de una imagen subida por formulario."""
    if file_storage is None or file_storage.filename == '':
        return False, 'Debes seleccionar una imagen.'

    filename = secure_filename(file_storage.filename)
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in ALLOWED_IMAGE_EXTENSIONS:
        return False, 'Formato de imagen no permitido.'

    if file_storage.content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return False, 'Tipo MIME no permitido para la portada.'

    return True, None


def is_valid_presigned_image_url(image_url: str) -> bool:
    """Acepta solo URLs del backend de storage configurado para evitar referencias arbitrarias."""
    if not image_url:
        return False
    storage_backend = current_app.config.get('STORAGE_BACKEND')
    if storage_backend == 'none':
        return False
    if storage_backend == 'local':
        # Normalize to prevent bypasses via backslashes, encoding, or multiple slashes
        target = unquote(image_url).replace('\\', '/')
        if target.startswith('//'):
            return False

        prefix = current_app.config['LOCAL_UPLOAD_URL_PATH'].rstrip('/') + '/'
        parsed = urlparse(target)
        if parsed.scheme or parsed.netloc:
            return False

        # os.path.normpath collapses redundancies like '..' and '.' (Security hardening)
        normalized_path = os.path.normpath(parsed.path).replace('\\', '/')
        # Ensure strict directory prefix matching
        norm_with_slash = normalized_path if normalized_path.endswith('/') else normalized_path + '/'
        return norm_with_slash.startswith(prefix)

    parsed = urlparse(image_url)
    bucket_name = current_app.config['S3_BUCKET_NAME']
    region = current_app.config['S3_REGION']
    expected_host = f'{bucket_name}.s3.{region}.amazonaws.com'
    return parsed.scheme == 'https' and parsed.netloc == expected_host


def is_safe_url(target: str) -> bool:
    """Valida que una URL sea segura para redirección (misma host o relativa)."""
    if not target:
        return False
    # Normalizar backslashes a forward slashes (algunos navegadores los tratan igual)
    target = target.replace('\\', '/')
    ref_url = urlparse(request.host_url)
    # urljoin resuelve contra el host actual, manejando correctamente URLs relativas y múltiples slashes
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and \
           test_url.netloc == ref_url.netloc


def get_request_ip() -> str:
    """Obtiene la IP más confiable disponible para rate limiting blando por visitante."""
    # ProxyFix ya se encarga de extraer la IP correcta de X-Forwarded-For si está configurado.
    return request.remote_addr or 'unknown'


def procesar_imagen_base64(archivo):
    """Procesa una imagen en memoria para la demo pública."""
    try:
        if archivo is None or archivo.filename == '':
            return None

        imagen_bytes = archivo.read()
        content_type = archivo.content_type or 'image/jpeg'
        imagen_base64 = base64.b64encode(imagen_bytes).decode('utf-8')
        return f'data:{content_type};base64,{imagen_base64}'
    except Exception as exc:
        current_app.logger.error('demo_image_processing_failed error=%s', exc)
        return None


def subir_imagen_a_s3(archivo):
    """Sube una portada usando el backend de storage disponible."""
    storage_backend = current_app.config.get('STORAGE_BACKEND')
    if storage_backend == 'none':
        current_app.logger.info('image_upload_skipped storage_backend=none')
        return None

    valid, error = is_valid_image_file(archivo)
    if not valid:
        current_app.logger.warning('image_validation_failed reason=%s', error)
        return None

    try:
        extension = os.path.splitext(secure_filename(archivo.filename))[1].lower()
        nombre_unico = f"covers/{uuid.uuid4()}{extension}"
        if storage_backend == 'local':
            upload_dir = os.path.join(current_app.config['LOCAL_UPLOAD_DIR'], 'covers')
            os.makedirs(upload_dir, exist_ok=True)
            destination = os.path.join(upload_dir, os.path.basename(nombre_unico))
            archivo.save(destination)
            return f"{current_app.config['LOCAL_UPLOAD_URL_PATH']}/{nombre_unico}"

        current_app.logger.warning(
            'image_upload_not_implemented storage_backend=%s object_key=%s',
            storage_backend,
            nombre_unico,
        )
        return None
    except Exception as exc:
        current_app.logger.error('image_upload_unexpected_error error=%s', exc)
        return None


def enviar_email_reset_password(destinatario: str, token: str) -> bool:
    """Envía el correo de recuperación con enlace directo."""
    try:
        if current_app.config.get('MAIL_SUPPRESS_SEND'):
            current_app.logger.warning('password_reset_email_suppressed email=%s', destinatario)
            return False

        reset_url = url_for('main.reset_password_with_email', token=token, _external=True)
        expiry_minutes = current_app.config['RESET_TOKEN_EXPIRY_MINUTES']

        message = Message(
            subject='Recuperacion de contraseña - GameVault',
            recipients=[destinatario],
            html=f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #1d4ed8;">Recupera tu acceso</h2>
                <p>Recibimos una solicitud para restablecer la contraseña de tu cuenta.</p>
                <p>Haz clic en el siguiente enlace para crear una nueva contraseña:</p>
                <p style="text-align: center; margin: 24px 0;">
                    <a href="{reset_url}" style="background: #1d4ed8; color: white; padding: 12px 24px; text-decoration: none; border-radius: 10px; display: inline-block;">Restablecer contraseña</a>
                </p>
                <p>Este enlace expira en {expiry_minutes} minutos.</p>
                <p>Si no solicitaste este cambio, puedes ignorar este correo.</p>
            </div>
            """,
        )
        mail.send(message)
        return True
    except Exception as exc:
        current_app.logger.error('password_reset_email_failed email=%s error=%s', destinatario, exc)
        return False


def paginate_items(items, page: int, per_page: int) -> dict:
    """Paginación simple sobre listas en memoria."""
    total_items = len(items)
    total_pages = max(1, math.ceil(total_items / per_page)) if per_page else 1
    current_page = max(1, min(page, total_pages))
    start = (current_page - 1) * per_page
    end = start + per_page
    return {
        'items': items[start:end],
        'page': current_page,
        'per_page': per_page,
        'total_items': total_items,
        'total_pages': total_pages,
        'has_prev': current_page > 1,
        'has_next': current_page < total_pages,
        'prev_page': current_page - 1,
        'next_page': current_page + 1,
    }


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Convierte strings ISO del dominio a datetimes comparables."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


# Bolt Optimization: constants and helpers for efficient date handling across routes.
MIN_DATE = datetime(1, 1, 1, tzinfo=timezone.utc)


def ensure_dt(val: str | datetime | None) -> datetime:
    """Asegura que el valor sea un datetime comparable (UTC aware)."""
    if val is None:
        return MIN_DATE
    if isinstance(val, str):
        return parse_iso_datetime(val) or MIN_DATE
    if val.tzinfo is None:
        return val.replace(tzinfo=timezone.utc)
    return val


def normalize_game_metadata(form) -> dict:
    """Normaliza campos opcionales para enriquecer la colección."""
    plataforma = (form.get('plataforma') or 'PC').strip()
    estado = (form.get('estado') or 'N/A').strip()
    categoria = (form.get('categoria') or 'Biblioteca').strip()
    prioridad = (form.get('prioridad') or 'Media').strip()
    calificacion_raw = form.get('calificacion', '').strip()

    calificacion = None
    if calificacion_raw:
        try:
            calificacion = int(calificacion_raw)
        except ValueError:
            calificacion = None

    es_favorito = form.get('es_favorito') == 'on'

    # Strict validation against allowed options (Security hardening)
    if plataforma not in GAME_PLATFORM_OPTIONS:
        plataforma = 'PC'
    if estado not in GAME_CONDITION_OPTIONS:
        estado = 'N/A'
    if categoria not in GAME_CATEGORY_OPTIONS:
        categoria = 'Biblioteca'
    if prioridad not in GAME_PRIORITY_OPTIONS:
        prioridad = 'Media'

    return {
        'plataforma': plataforma,
        'estado': estado,
        'categoria': categoria,
        'prioridad': prioridad,
        'calificacion': calificacion if calificacion in GAME_RATING_OPTIONS else None,
        'es_favorito': es_favorito,
    }


def build_dashboard_insights(juegos: list[dict], activity_logs: list[dict] | None = None) -> dict:
    """Calcula métricas ligeras para el dashboard (Optimización Bolt: datetime comparisons)."""
    now = datetime.now(timezone.utc)
    recent_cutoff = now - timedelta(days=7)
    stale_cutoff = now - timedelta(days=30)
    # Datetime comparisons are much faster than ISO string generation and comparison.
    recent_cutoff_iso = recent_cutoff.isoformat()

    platform_counts, status_counts, category_counts = Counter(), Counter(), Counter()

    recently_updated = recently_added = missing_images = favorites_count = 0
    high_priority_count = stale_games = ratings_sum = ratings_count = 0
    next_focus = next_focus_at = None

    # Database already orders by updated_at DESC, created_at DESC, so we get O(1) detection.
    last_updated_game = juegos[0] if juegos else None

    for juego in juegos:
        plat = juego.get('plataforma')
        platform_counts[plat or 'Sin plataforma'] += 1

        est = juego.get('estado')
        status_counts[est or 'N/A'] += 1

        cat = juego.get('categoria') or 'Biblioteca'
        category_counts[cat] += 1

        if not juego.get('imagen_url'):
            missing_images += 1
        if juego.get('es_favorito'):
            favorites_count += 1

        # Check for 'Alta' priority directly and nest next_focus logic to reduce branching
        prio = juego.get('prioridad')
        dt_created = ensure_dt(juego.get('created_at'))
        dt_updated = ensure_dt(juego.get('updated_at'))
        if dt_updated == MIN_DATE:
            dt_updated = dt_created

        if prio == 'Alta':
            high_priority_count += 1
            if cat != 'Completado':
                if dt_updated != MIN_DATE:
                    if next_focus_at is None or dt_updated < next_focus_at:
                        next_focus, next_focus_at = juego, dt_updated

        calif = juego.get('calificacion')
        if isinstance(calif, int):
            ratings_sum += calif
            ratings_count += 1

        if dt_created != MIN_DATE and dt_created >= recent_cutoff:
            recently_added += 1

        if dt_updated != MIN_DATE and dt_updated >= recent_cutoff:
            recently_updated += 1
        if dt_updated != MIN_DATE and dt_updated < stale_cutoff:
            stale_games += 1

    recent_activity = 0
    if activity_logs:
        for log in activity_logs:
            ts_iso = log.get('timestamp')
            # Activity logs still use ISO strings for now as they are fewer.
            if ts_iso and ts_iso >= recent_cutoff_iso:
                recent_activity += 1
            else:
                break  # O(1) short-circuit as logs are already sorted by timestamp desc.

    dominant_platform = platform_counts.most_common(1)[0] if platform_counts else ('Sin juegos', 0)
    dominant_status = status_counts.most_common(1)[0] if status_counts else ('N/A', 0)
    dominant_category = category_counts.most_common(1)[0] if category_counts else ('Biblioteca', 0)

    # Derive unique values from Counters to avoid redundant set operations during the loop.
    return {
        'total_games': len(juegos),
        'platforms_count': len(platform_counts),
        'recently_added': recently_added,
        'recently_updated': recently_updated,
        'recent_activity': recent_activity,
        'missing_images': missing_images,
        'favorites_count': favorites_count,
        'high_priority_count': high_priority_count,
        'stale_games': stale_games,
        'wishlist_count': category_counts.get('Wishlist', 0),
        'backlog_count': category_counts.get('Backlog', 0),
        'currently_playing_count': category_counts.get('Jugando', 0),
        'average_rating': round(ratings_sum / ratings_count, 1) if ratings_count > 0 else None,
        'dominant_platform': {'label': dominant_platform[0], 'count': dominant_platform[1]},
        'dominant_status': {'label': dominant_status[0], 'count': dominant_status[1]},
        'dominant_category': {'label': dominant_category[0], 'count': dominant_category[1]},
        'last_updated_game': last_updated_game,
        'next_focus': next_focus,
        'filter_options': {
            'plataformas': sorted(p for p in platform_counts if p != 'Sin plataforma'),
            'estados': sorted(s for s in status_counts if s != 'N/A'),
            'categorias': sorted(category_counts),
        }
    }


def build_reset_debug_context(email: str, token: str, expires_at) -> dict:
    """Construye datos de apoyo local para recuperar acceso sin correo real."""
    return {
        'email': email,
        'token': token,
        'expires_at': expires_at,
        'reset_url': url_for('main.reset_password_with_email', token=token, email=email, _external=True),
        'validate_url': url_for('main.validate_token_page'),
    }


def get_action_badge_class(action: str) -> str:
    """Asigna color visual según el tipo de actividad auditada (Optimizado: O(1))."""
    return _ACTION_BADGE_MAP.get((action or '').upper(), 'action-generic')


def build_admin_log_groups(logs: list[dict]) -> list[dict]:
    """Agrupa logs por cuenta (optimizado: asume logs ya ordenados por timestamp desc)."""
    # Pre-fetch de todos los usuarios únicos para evitar N+1 queries.
    unique_user_ids = {log.get('user_id') for log in logs if log.get('user_id')}
    users_data = obtener_usuarios_por_ids(list(unique_user_ids))
    user_cache = {u['user_id']: u for u in users_data}

    grouped: dict[str, dict] = {}

    for log in logs:
        user_id = log.get('user_id') or 'system'
        if user_id not in grouped:
            user = user_cache.get(user_id)
            grouped[user_id] = {
                'user_id': user_id,
                'email': (user or {}).get('email', '') if user_id != 'system' else 'sistema@local',
                'nombre': (user or {}).get('nombre', '') if user_id != 'system' else 'Sistema',
                'items': [],
                'latest_timestamp': log.get('timestamp', ''),
                'latest_action': log.get('action_name') or log.get('action') or 'Actividad',
            }
        bucket = grouped[user_id]
        # Mutate the log dict in-place instead of copying to reduce allocations during admin view loads.
        log['action_badge_class'] = get_action_badge_class(log.get('action', ''))
        log['status_badge_class'] = (
            'badge-log-success'
            if log.get('status') == 'SUCCESS'
            else 'badge-log-error'
            if log.get('status') in {'FAILED', 'ERROR'}
            else 'badge-log-neutral'
        )
        bucket['items'].append(log)

    ordered_groups = list(grouped.values())
    for group in ordered_groups:
        group['events_count'] = len(group['items'])
    return ordered_groups


def build_query_args(**updates) -> dict:
    """Conserva filtros activos al paginar o cambiar orden."""
    args = dict(request.args)
    for key, value in updates.items():
        if value in (None, '', []):
            args.pop(key, None)
        else:
            args[key] = value
    return args


def filter_and_sort_games(juegos, filters):
    """Aplica búsqueda, filtros y orden en memoria (Optimizado)."""
    query = filters.get('q', '').strip().lower()
    plataforma = filters.get('plataforma', '')
    estado = filters.get('estado', '')
    categoria = filters.get('categoria', '')
    favoritos = filters.get('favoritos', '')
    sort_by = filters.get('sort', 'updated_desc')

    # Short-circuit: if no filters and default sort, return as is (DB already sorted it).
    if not any([query, plataforma, estado, categoria, favoritos]) and sort_by == 'updated_desc':
        return juegos

    filtered = []
    for juego in juegos:
        # Chequeos baratos primero para fallar rápido antes de construir el haystack
        if plataforma and juego.get('plataforma') != plataforma:
            continue
        if estado and juego.get('estado') != estado:
            continue
        if categoria and juego.get('categoria') != categoria:
            continue
        if favoritos == 'solo' and not juego.get('es_favorito'):
            continue

        # La búsqueda por texto es la operación más costosa, optimizada con short-circuit
        if query and not (
            query in (juego.get('titulo') or '').lower() or
            query in (juego.get('plataforma') or '').lower() or
            query in (juego.get('estado') or '').lower() or
            query in (juego.get('descripcion') or '').lower()
        ):
            continue

        filtered.append(juego)

    def sort_key(item):
        updated = ensure_dt(item.get('updated_at'))
        if updated != MIN_DATE:
            return updated
        return ensure_dt(item.get('created_at'))

    reverse = True
    if sort_by == 'title_asc':
        reverse = False
        filtered.sort(key=lambda item: item.get('titulo', '').lower())
    elif sort_by == 'title_desc':
        filtered.sort(key=lambda item: item.get('titulo', '').lower(), reverse=True)
    elif sort_by == 'created_asc':
        reverse = False
        filtered.sort(key=lambda item: ensure_dt(item.get('created_at')), reverse=reverse)
    elif sort_by == 'created_desc':
        filtered.sort(key=lambda item: ensure_dt(item.get('created_at')), reverse=True)
    elif sort_by == 'updated_desc':
        # Already ordered by DB (updated_at desc, created_at desc)
        pass
    else:
        filtered.sort(key=sort_key, reverse=True)

    return filtered


def enrich_game_metadata(game: dict | None) -> dict | None:
    """Enriquece el juego con URL de imagen y serializa fechas (Optimización Bolt: in-place)."""
    if game is None:
        return None

    game['imagen_url'] = crear_url_firmada_lectura(game.get('imagen_url', ''))

    # Bolt Optimization: Convert raw datetimes to ISO strings only when needed for templates.
    for field in ('updated_at', 'created_at'):
        val = game.get(field)
        if isinstance(val, datetime):
            game[field] = as_iso(val)

    return game


@main_bp.route('/')
def landing():
    """Landing pública orientada a coleccionistas."""
    public_collections = aplicar_ratings_showcase(
        obtener_colecciones_publicas(limit=6),
        subject_type='public',
        subject_id_key='user_id',
    )
    # Creamos copias de las colecciones de ejemplo para que la mutación in-place de
    # aplicar_ratings_showcase no afecte a la constante global entre peticiones.
    sample_collections = aplicar_ratings_showcase(
        [dict(item) for item in LANDING_SAMPLE_COLLECTIONS],
        subject_type='sample',
        subject_id_key='id',
        default_rating_key='average_rating',
        default_votes_key='base_votes_count',
    )
    return render_template(
        'landing.html',
        public_collections=public_collections,
        sample_collections=sample_collections,
    )


@main_bp.route('/api/showcase/rate', methods=['POST'])
@limiter.limit('10 per minute')
def rate_showcase():
    """Permite valorar colecciones públicas o demo, una vez por IP y colección."""
    payload = request.get_json(silent=True) or {}
    raw_subject_type = payload.get('subject_type')
    raw_subject_id = payload.get('subject_id')

    # Convert to safe strings for internal processing
    subject_type = str(raw_subject_type or '').strip().lower()
    subject_id = str(raw_subject_id or '').strip()

    try:
        rating = int(payload.get('rating'))
    except (TypeError, ValueError):
        rating = 0

    # Defensive input validation matching DB constraints (Security enhancement)
    # We check that the payload values were originally expected types to avoid bypasses or logic errors
    if (
        not isinstance(raw_subject_type, str)
        or not isinstance(raw_subject_id, (str, int))
        or subject_type not in {'sample', 'public'}
        or not subject_id
        or len(subject_type) > 20
        or len(subject_id) > 120
        or rating not in {1, 2, 3, 4, 5}
    ):
        crear_log_audit(
            user_id=None,
            action='RATE_SHOWCASE',
            resource='showcase_ratings',
            details={
                # Truncate raw values to prevent log-injection/DoS via oversized details (Security hardening)
                'subject_type': str(raw_subject_type)[:40],
                'subject_id': str(raw_subject_id)[:200],
                'rating': rating,
                'reason': 'invalid_input',
            },
            ip_address=get_request_ip(),
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        return jsonify({'error': 'Datos de valoración inválidos.'}), 400

    if subject_type == 'sample':
        valid_ids = {item['id'] for item in LANDING_SAMPLE_COLLECTIONS}
        if subject_id not in valid_ids:
            return jsonify({'error': 'Colección de ejemplo no encontrada.'}), 404
    else:
        visible_public_ids = {item['user_id'] for item in obtener_colecciones_publicas(limit=100)}
        if subject_id not in visible_public_ids:
            return jsonify({'error': 'Colección pública no disponible para portada.'}), 404

    result = registrar_rating_showcase(subject_type, subject_id, rating, get_request_ip())

    crear_log_audit(
        user_id=None,
        action='RATE_SHOWCASE',
        resource='showcase_ratings',
        details={'subject_type': subject_type, 'subject_id': subject_id, 'rating': rating},
        ip_address=get_request_ip(),
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS' if result.get('success') else 'FAILED',
    )

    if subject_type == 'sample' and ('average' in result or 'votes_count' in result):
        sample_entry = next((item for item in LANDING_SAMPLE_COLLECTIONS if item['id'] == subject_id), None)
        if sample_entry is not None:
            merged_summary = combinar_rating_showcase(
                {
                    'average': result.get('average'),
                    'votes_count': result.get('votes_count'),
                },
                base_average=sample_entry.get('average_rating'),
                base_votes_count=sample_entry.get('base_votes_count', 0),
            )
            result['average'] = merged_summary['average']
            result['votes_count'] = merged_summary['votes_count']
    status_code = 409 if result.get('duplicate') else 200 if result.get('success') else 400
    return jsonify(result), status_code


@main_bp.route('/privacy')
def privacy():
    """Página simple de privacidad."""
    return render_template('privacy.html')


@main_bp.route('/terms')
def terms():
    """Página simple de términos y condiciones."""
    return render_template('terms.html')


@main_bp.route('/demo', methods=['GET', 'POST'])
@limiter.limit('5 per minute', methods=['POST'])
def demo():
    """Demo pública sin persistencia."""
    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        imagen = request.files.get('imagen')

        if not titulo:
            flash('El título es requerido.', 'error')
            return redirect(url_for('main.demo'))

        valid, error = is_valid_image_file(imagen)
        if not valid:
            flash(error, 'error')
            return redirect(url_for('main.demo'))

        imagen_base64 = procesar_imagen_base64(imagen)
        if imagen_base64 is None:
            flash('No se pudo procesar la imagen de la demo.', 'error')
            return redirect(url_for('main.demo'))

        return render_template(
            'demo_result.html',
            titulo=titulo,
            imagen_base64=imagen_base64,
            filename=imagen.filename,
        )

    return render_template('demo_form.html')


@main_bp.route('/healthz')
def healthz():
    """Healthcheck apto para monitoreo."""
    return {
        'status': 'ok',
        'app': 'GameVault',
        'env': current_app.config['APP_ENV'],
        'database': current_app.config['DATABASE_BACKEND'],
        'database_ok': database_healthcheck(),
        'storage': current_app.config['STORAGE_BACKEND'],
    }


@main_bp.route('/salud')
def salud():
    """Alias legado del healthcheck."""
    return healthz()


@main_bp.route('/dashboard')
@require_login
def dashboard():
    """Dashboard privado con búsqueda, filtros y paginación."""
    if session.get('role') == 'admin':
        return redirect(url_for('main.admin_panel'))
    user_id = session['user_id']
    juegos = obtener_juegos_por_usuario(user_id)
    filters = {
        'q': request.args.get('q', ''),
        'plataforma': request.args.get('plataforma', ''),
        'estado': request.args.get('estado', ''),
        'categoria': request.args.get('categoria', ''),
        'favoritos': request.args.get('favoritos', ''),
        'sort': request.args.get('sort', 'updated_desc'),
    }
    page = request.args.get('page', 1, type=int)

    filtered_games = filter_and_sort_games(juegos, filters)
    dashboard_insights = build_dashboard_insights(juegos)
    pagination = paginate_items(filtered_games, page, current_app.config['GAMES_PER_PAGE'])

    # Bolt Optimization: Enriquecer solo los juegos de la página actual y los destacados del dashboard.
    paginated_games = [enrich_game_metadata(juego) for juego in pagination['items']]
    enrich_game_metadata(dashboard_insights.get('last_updated_game'))
    enrich_game_metadata(dashboard_insights.get('next_focus'))

    filter_opts = dashboard_insights.get('filter_options', {})

    return render_template(
        'index.html',
        juegos=paginated_games,
        dashboard_insights=dashboard_insights,
        filters=filters,
        pagination=pagination,
        total_user_games=len(juegos),
        total_filtered_games=len(filtered_games),
        plataformas=filter_opts.get('plataformas', []),
        estados=filter_opts.get('estados', []),
        categorias=filter_opts.get('categorias', []),
        GAME_PLATFORM_OPTIONS=GAME_PLATFORM_OPTIONS,
        GAME_CONDITION_OPTIONS=GAME_CONDITION_OPTIONS,
        GAME_CATEGORY_OPTIONS=GAME_CATEGORY_OPTIONS,
        GAME_PRIORITY_OPTIONS=GAME_PRIORITY_OPTIONS,
        GAME_RATING_OPTIONS=GAME_RATING_OPTIONS,
        query_args_builder=build_query_args,
    )


@main_bp.route('/api/uploads/presign', methods=['POST'])
@require_login
@limiter.limit('10 per minute')
def presign_upload():
    """Genera credenciales temporales para subir portadas directo al storage configurado."""
    if current_app.config.get('STORAGE_BACKEND') == 'none':
        return jsonify({'error': 'El almacenamiento de imagenes aun no esta configurado.'}), 503

    filename = request.form.get('filename', '').strip() or (request.json or {}).get('filename', '').strip()
    content_type = request.form.get('content_type', '').strip() or (request.json or {}).get('content_type', '').strip()

    if not filename or not content_type:
        return jsonify({'error': 'filename y content_type son obligatorios'}), 400

    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if extension not in ALLOWED_IMAGE_EXTENSIONS or content_type not in ALLOWED_IMAGE_MIME_TYPES:
        return jsonify({'error': 'Archivo no permitido'}), 400

    try:
        payload = crear_presigned_upload(
            filename,
            content_type,
            current_app.config['MAX_IMAGE_UPLOAD_BYTES'],
        )
        return jsonify(payload)
    except Exception as exc:
        current_app.logger.error('presign_upload_failed error=%s', exc)
        return jsonify({'error': 'No se pudo generar la carga firmada'}), 500


@main_bp.route('/agregar', methods=['POST'])
@require_login
@limiter.limit('10 per minute')
def agregar_juego():
    """Crea un juego nuevo para el usuario autenticado."""
    titulo = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    plataforma_raw = request.form.get('plataforma', 'PC').strip()
    estado_raw = request.form.get('estado', 'N/A').strip()
    metadata = normalize_game_metadata(request.form)
    imagen = request.files.get('imagen')
    imagen_url = request.form.get('imagen_url', '').strip()

    errores = []
    if not titulo:
        errores.append('El título es requerido.')
    elif len(titulo) > 255:
        errores.append('El título es demasiado largo (máximo 255 caracteres).')
    if not descripcion:
        errores.append('La descripción es requerida.')
    elif len(descripcion) > 5000:
        errores.append('La descripción es demasiado larga (máximo 5000 caracteres).')

    # Basic length checks for metadata (Security hardening)
    if len(plataforma_raw) > 80:
        errores.append('El nombre de la plataforma es demasiado largo.')
    if len(estado_raw) > 80:
        errores.append('El estado es demasiado largo.')

    if imagen_url:
        if not is_valid_presigned_image_url(imagen_url):
            errores.append('La portada generada no pertenece al bucket configurado.')
    elif imagen and imagen.filename:
        valid, error = is_valid_image_file(imagen)
        if not valid:
            errores.append(error)
        elif current_app.config.get('STORAGE_BACKEND') == 'none':
            errores.append('Las portadas aun no estan configuradas. Guarda el juego sin imagen por ahora.')

    if errores:
        for error in errores:
            flash(error, 'error')
        return redirect(url_for('main.dashboard'))

    if not imagen_url and imagen and imagen.filename:
        imagen_url = subir_imagen_a_s3(imagen)

    if imagen and imagen.filename and not imagen_url:
        flash('No se pudo subir la portada.', 'error')
        return redirect(url_for('main.dashboard'))

    game_id = str(uuid.uuid4())
    resultado = crear_juego(
        session['user_id'],
        game_id,
        titulo,
        descripcion,
        imagen_url,
        metadata['plataforma'],
        metadata['estado'],
        metadata['categoria'],
        metadata['prioridad'],
        metadata['calificacion'],
        metadata['es_favorito'],
    )
    if not resultado:
        flash('Error al guardar el juego.', 'error')
        return redirect(url_for('main.dashboard'))

    crear_log_audit(
        user_id=session['user_id'],
        action='CREATE_GAME',
        resource='games',
        details={
            'game_id': game_id,
            'title': titulo,
            'categoria': metadata['categoria'],
            'prioridad': metadata['prioridad'],
            'es_favorito': metadata['es_favorito'],
        },
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash(f'Juego "{titulo}" agregado exitosamente.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/delete/<game_id>', methods=['POST'])
@require_login
@limiter.limit('10 per minute')
def eliminar_juego_ruta(game_id):
    """Elimina un juego del usuario autenticado."""
    user_id = session['user_id']
    juego = obtener_juego_por_id(user_id, game_id)
    if juego is None:
        flash('Juego no encontrado o sin permisos.', 'error')
        return redirect(url_for('main.dashboard'))

    resultado = eliminar_juego(user_id, game_id)
    if not resultado['success']:
        flash(f'No se pudo eliminar el juego: {resultado.get("error", "desconocido")}', 'error')
        return redirect(url_for('main.dashboard'))

    crear_log_audit(
        user_id=user_id,
        action='DELETE_GAME',
        resource='games',
        details={'game_id': game_id, 'title': juego.get('titulo')},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash(f'Juego "{juego.get("titulo", "sin título")}" eliminado.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/edit/<game_id>', methods=['GET', 'POST'])
@require_login
@limiter.limit('10 per minute', methods=['POST'])
def editar_juego_ruta(game_id):
    """Edita un juego existente."""
    user_id = session['user_id']
    juego = obtener_juego_por_id(user_id, game_id)
    if juego is None:
        flash('Juego no encontrado o sin permisos.', 'error')
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template(
            'edit_game.html',
            juego=enrich_game_metadata(juego),
            GAME_PLATFORM_OPTIONS=GAME_PLATFORM_OPTIONS,
            GAME_CONDITION_OPTIONS=GAME_CONDITION_OPTIONS,
            GAME_CATEGORY_OPTIONS=GAME_CATEGORY_OPTIONS,
            GAME_PRIORITY_OPTIONS=GAME_PRIORITY_OPTIONS,
            GAME_RATING_OPTIONS=GAME_RATING_OPTIONS,
        )

    titulo = request.form.get('titulo', '').strip()
    descripcion = request.form.get('descripcion', '').strip()
    plataforma_raw = request.form.get('plataforma', 'PC').strip()
    estado_raw = request.form.get('estado', 'N/A').strip()
    metadata = normalize_game_metadata(request.form)
    nueva_imagen = request.files.get('nueva_imagen')
    nueva_imagen_url = request.form.get('nueva_imagen_url', '').strip()

    errores = []
    if not titulo:
        errores.append('El título es requerido.')
    elif len(titulo) > 255:
        errores.append('El título es demasiado largo (máximo 255 caracteres).')
    if not descripcion:
        errores.append('La descripción es requerida.')
    elif len(descripcion) > 5000:
        errores.append('La descripción es demasiado larga (máximo 5000 caracteres).')

    # Basic length checks for metadata (Security hardening)
    if len(plataforma_raw) > 80:
        errores.append('El nombre de la plataforma es demasiado largo.')
    if len(estado_raw) > 80:
        errores.append('El estado es demasiado largo.')

    if nueva_imagen_url and not is_valid_presigned_image_url(nueva_imagen_url):
        errores.append('La nueva portada generada no es válida.')
    elif nueva_imagen and nueva_imagen.filename:
        valid, error = is_valid_image_file(nueva_imagen)
        if not valid:
            errores.append(error)
        elif current_app.config.get('STORAGE_BACKEND') == 'none':
            errores.append('Las portadas aun no estan configuradas. Guarda los cambios sin imagen por ahora.')

    if errores:
        for error in errores:
            flash(error, 'error')
        return redirect(url_for('main.editar_juego_ruta', game_id=game_id))

    resultado = actualizar_juego(
        user_id,
        game_id,
        {
            'titulo': titulo,
            'descripcion': descripcion,
            'plataforma': metadata['plataforma'],
            'estado': metadata['estado'],
            'categoria': metadata['categoria'],
            'prioridad': metadata['prioridad'],
            'calificacion': metadata['calificacion'],
            'es_favorito': metadata['es_favorito'],
        },
        nueva_imagen_url or (nueva_imagen if nueva_imagen and nueva_imagen.filename else None),
    )

    if not resultado['success']:
        flash(f'No se pudo actualizar el juego: {resultado.get("error", "desconocido")}', 'error')
        return redirect(url_for('main.editar_juego_ruta', game_id=game_id))

    crear_log_audit(
        user_id=user_id,
        action='UPDATE_GAME',
        resource='games',
        details={
            'game_id': game_id,
            'title': titulo,
            'categoria': metadata['categoria'],
            'prioridad': metadata['prioridad'],
            'es_favorito': metadata['es_favorito'],
        },
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash(f'Juego "{titulo}" actualizado.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/registro', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
def registro():
    """Registro simplificado para coleccionistas."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('registro.html')

    nombre = request.form.get('nombre', '').strip()
    email = request.form.get('email', '').strip().lower()
    prefijo_pais = request.form.get('prefijo_pais', '').strip()
    telefono = request.form.get('telefono', '').strip()
    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()

    errores = []
    if not nombre:
        errores.append('El nombre es requerido.')
    elif len(nombre) > 120:
        errores.append('El nombre es demasiado largo (máximo 120 caracteres).')
    if not email:
        errores.append('El email es requerido.')
    elif not validar_email(email):
        errores.append('El formato o la longitud del email no son válidos.')
    if not password:
        errores.append('La contraseña es requerida.')
    elif not validar_password(password):
        errores.append('La contraseña debe tener entre 8 y 128 caracteres e incluir al menos una letra y un número.')
    if prefijo_pais and len(prefijo_pais) > 10:
        errores.append('El prefijo de país es demasiado largo (máximo 10 caracteres).')
    if telefono and not validar_telefono(telefono):
        errores.append('El teléfono debe contener entre 7 y 20 dígitos.')
    if password != confirm_password:
        errores.append('Las contraseñas no coinciden.')
    if obtener_usuario_por_email(email):
        errores.append('Ese correo ya está registrado.')

    if errores:
        for error in errores:
            flash(error, 'error')
        crear_log_audit(
            user_id=None,
            action='REGISTER',
            resource='users',
            details={'email': email, 'errors': errores},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        return redirect(url_for('main.registro'))

    password_hash = generate_password_hash(password)
    resultado = crear_usuario(nombre, '', email, prefijo_pais, telefono, password_hash)
    if not resultado:
        flash('No se pudo crear tu cuenta. Intenta de nuevo.', 'error')
        return redirect(url_for('main.registro'))

    session.clear()
    session.permanent = True
    session['user_id'] = resultado['user_id']
    session['email'] = resultado['email']
    session['nombre'] = resultado['nombre']
    session['role'] = resultado.get('role', 'user')
    # Store a SHA256 of the password hash to detect changes and invalidate other sessions
    session['_pw_hash'] = hashlib.sha256(password_hash.encode('utf-8')).hexdigest()

    crear_log_audit(
        user_id=resultado['user_id'],
        action='REGISTER',
        resource='users',
        details={'email': email},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash(f'Bienvenido a GameVault, {nombre}.', 'success')
    return redirect(url_for('main.dashboard'))


@main_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('5 per minute', methods=['POST'])
def login():
    """Inicio de sesión con rate limiting."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('login.html')

    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '').strip()
    if not email or not password:
        flash('Email y contraseña son requeridos.', 'error')
        return redirect(url_for('main.login'))

    usuario = verificar_credenciales(email, password)

    # Use a dummy hash for missing users to mitigate timing attacks (Security enhancement)
    # This prevents attackers from discovering valid emails by measuring response times.
    dummy_hash = 'scrypt:32768:8:1$I5M8muL7dw4n9QXZ$e6f7a505f876cee29b89fd0fb1fd13f8be1ac953c9b6dea87709cb9cd105c8525ad2854e1400b5de5e36b405c189a247bf212008e6259277e98a71392edcd920'
    db_hash = usuario['password_hash'] if usuario else dummy_hash
    password_correct = check_password_hash(db_hash, password)

    if (
        usuario is None
        or usuario.get('status') != 'active'
        or not password_correct
    ):
        crear_log_audit(
            user_id=usuario['user_id'] if usuario else None,
            action='FAILED_LOGIN',
            resource='auth',
            details={'email': email, 'reason': 'invalid_credentials_or_inactive'},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        flash('Email o contraseña incorrectos.', 'error')
        return redirect(url_for('main.login'))

    session.clear()
    session.permanent = True
    session['user_id'] = usuario['user_id']
    session['email'] = usuario['email']
    session['nombre'] = usuario['nombre']
    session['role'] = usuario.get('role', 'user')
    # Store a SHA256 of the password hash to detect changes and invalidate other sessions
    session['_pw_hash'] = hashlib.sha256(usuario['password_hash'].encode('utf-8')).hexdigest()

    crear_log_audit(
        user_id=usuario['user_id'],
        action='LOGIN',
        resource='auth',
        details={'email': email},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )

    next_url = request.args.get('next')
    if next_url and is_safe_url(next_url):
        return redirect(next_url)
    if session.get('role') == 'admin':
        return redirect(url_for('main.admin_panel'))
    return redirect(url_for('main.dashboard'))


@main_bp.route('/logout', methods=['POST'])
@require_login
@limiter.limit('5 per minute')
def logout():
    """Cierra sesión solo por POST."""
    user_id = session.get('user_id')
    email = session.get('email')
    nombre = session.get('nombre', 'Usuario')
    crear_log_audit(
        user_id=user_id,
        action='LOGOUT',
        resource='auth',
        details={'email': email},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    session.clear()
    flash(f'Has cerrado sesión, {nombre}.', 'success')
    return redirect(url_for('main.landing'))


@main_bp.route('/perfil', methods=['GET', 'POST'])
@require_login
@limiter.limit('10 per minute', methods=['POST'])
def profile():
    """Permite editar perfil y contraseña."""
    if session.get('role') == 'admin':
        return redirect(url_for('main.admin_panel'))
    # Use g.current_user cached by @require_login to avoid redundant DB query
    user = g.current_user
    juegos = obtener_juegos_por_usuario(session['user_id'])
    recent_activity_logs = obtener_logs_por_usuario(session['user_id'], limit=8)
    profile_insights = build_dashboard_insights(juegos)

    # Bolt Optimization: Serializar metadatos de los destacados del perfil.
    enrich_game_metadata(profile_insights.get('last_updated_game'))
    enrich_game_metadata(profile_insights.get('next_focus'))

    if request.method == 'GET':
        return render_template(
            'profile.html',
            user=user,
            profile_insights=profile_insights,
            recent_activity_logs=recent_activity_logs,
        )

    form_name = request.form.get('form_name', 'profile')

    if form_name == 'password':
        current_password = request.form.get('current_password', '').strip()
        password = request.form.get('password', '').strip()
        confirm_password = request.form.get('confirm_password', '').strip()

        errores = []
        if not check_password_hash(user['password_hash'], current_password):
            crear_log_audit(
                user_id=session['user_id'],
                action='CHANGE_PASSWORD',
                resource='users',
                details={'email': session.get('email'), 'reason': 'incorrect_current_password'},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='FAILED',
            )
            errores.append('La contraseña actual no es correcta.')
        if not validar_password(password):
            errores.append('La nueva contraseña debe tener entre 8 y 128 caracteres e incluir al menos una letra y un número.')
        if password != confirm_password:
            errores.append('Las contraseñas no coinciden.')

        if errores:
            for error in errores:
                flash(error, 'error')
            return redirect(url_for('main.profile'))

        resultado = actualizar_password_usuario(session['user_id'], generate_password_hash(password))
        if not resultado['success']:
            flash(f'No se pudo actualizar la contraseña: {resultado["error"]}', 'error')
            return redirect(url_for('main.profile'))

        crear_log_audit(
            user_id=session['user_id'],
            action='CHANGE_PASSWORD',
            resource='users',
            details={'email': session.get('email')},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='SUCCESS',
        )
        session.clear()
        flash('Tu contraseña fue actualizada. Por favor inicia sesión de nuevo.', 'success')
        return redirect(url_for('main.login'))

    nombre = request.form.get('nombre', '').strip()
    apellido = request.form.get('apellido', '').strip()
    prefijo_pais = request.form.get('prefijo_pais', '').strip()
    telefono = request.form.get('telefono', '').strip()
    collection_visibility = request.form.get('collection_visibility', 'private').strip().lower()
    homepage_showcase_opt_in = request.form.get('homepage_showcase_opt_in') == 'on'

    errores = []
    if not nombre:
        errores.append('El nombre es requerido.')
    elif len(nombre) > 120:
        errores.append('El nombre es demasiado largo (máximo 120 caracteres).')
    if len(apellido) > 120:
        errores.append('El apellido es demasiado largo (máximo 120 caracteres).')
    if len(prefijo_pais) > 10:
        errores.append('El prefijo de país es demasiado largo.')
    if telefono and not validar_telefono(telefono):
        errores.append('El teléfono debe contener entre 7 y 20 dígitos.')

    if errores:
        for error in errores:
            flash(error, 'error')
        return redirect(url_for('main.profile'))

    resultado = actualizar_usuario_perfil(
        session['user_id'],
        {
            'nombre': nombre,
            'apellido': apellido,
            'prefijo_pais': prefijo_pais,
            'telefono': telefono,
            'collection_visibility': collection_visibility,
            'homepage_showcase_opt_in': homepage_showcase_opt_in and collection_visibility == 'public',
        },
    )
    if not resultado['success']:
        flash(f'No se pudo actualizar el perfil: {resultado["error"]}', 'error')
        return redirect(url_for('main.profile'))

    session['nombre'] = nombre
    crear_log_audit(
        user_id=session['user_id'],
        action='UPDATE_PROFILE',
        resource='users',
        details={'email': session.get('email')},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash('Perfil actualizado correctamente.', 'success')
    return redirect(url_for('main.profile'))


@main_bp.route('/forgot-password', methods=['GET', 'POST'])
@limiter.limit('3 per hour', methods=['POST'])
def forgot_password():
    """Solicita recuperación de contraseña sin revelar existencia del usuario."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('forgot_password.html')

    email = request.form.get('email', '').strip().lower()
    if not email:
        flash('El email es requerido.', 'error')
        return redirect(url_for('main.forgot_password'))

    user = obtener_usuario_por_email(email)
    flash('Si el correo está registrado, recibirás un enlace para recuperar tu contraseña.', 'success')

    if not user or user.get('status') != 'active':
        crear_log_audit(
            user_id=user['user_id'] if user else None,
            action='PASSWORD_RESET_REQUEST',
            resource='auth',
            details={'email': email, 'reason': 'user_not_found_or_inactive'},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        return redirect(url_for('main.forgot_password'))

    if user and user.get('status') == 'active':
        result = crear_reset_token(user['user_id'], request.remote_addr or None)
        if result['success']:
            email_sent = enviar_email_reset_password(email, result['token'])
            crear_log_audit(
                user_id=user['user_id'],
                action='PASSWORD_RESET_REQUEST',
                resource='auth',
                details={'email': email},
                ip_address=request.remote_addr or 'unknown',
                user_agent=request.headers.get('User-Agent', 'unknown'),
                status='SUCCESS',
            )
            should_show_debug = current_app.config.get('SHOW_RESET_DEBUG_TOKEN') or (
                current_app.config.get('APP_ENV') != 'production' and not email_sent
            )
            if should_show_debug:
                if email_sent:
                    flash('Entorno de prueba: se muestra el acceso de recuperación para validar el flujo end-to-end.', 'warning')
                else:
                    flash('No se pudo enviar el correo automático. Usa este token temporal para continuar la recuperación.', 'warning')
                return render_template(
                    'forgot_password.html',
                    debug_reset=build_reset_debug_context(email, result['token'], result['expires_at']),
                    email_sent=email_sent,
                )
        else:
            current_app.logger.error('password_reset_token_creation_failed user_id=%s', user['user_id'])

    return redirect(url_for('main.forgot_password'))


@main_bp.route('/forgot-password/manual-token', methods=['POST'])
@limiter.limit('3 per hour', methods=['POST'])
def forgot_password_manual_token():
    """Permite recuperar token desde la web validando email + teléfono registrado."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    email = request.form.get('email', '').strip().lower()
    telefono = request.form.get('telefono', '').strip()
    if not email or not telefono:
        flash('Para la opción 2 debes indicar correo y teléfono.', 'error')
        return redirect(url_for('main.forgot_password'))

    user = obtener_usuario_por_email(email)
    # Validar si el usuario existe y el teléfono coincide
    if not user or str(user.get('telefono', '')).strip() != telefono or user.get('status') != 'active':
        crear_log_audit(
            user_id=user['user_id'] if user else None,
            action='PASSWORD_RESET_REQUEST',
            resource='auth',
            details={'email': email, 'reason': 'manual_token_validation_failed'},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        # En producción no revelamos si los datos son incorrectos para evitar enumeración.
        if not current_app.config.get('SHOW_RESET_DEBUG_TOKEN'):
            flash('Si tus datos coinciden, se ha procesado la solicitud. Contacta a soporte si necesitas ayuda adicional.', 'success')
            return redirect(url_for('main.forgot_password'))

        flash('No se pudo validar los datos de recuperación.', 'error')
        return redirect(url_for('main.forgot_password'))

    result = crear_reset_token(user['user_id'], request.remote_addr or None)
    if not result.get('success'):
        flash('No se pudo generar el token de recuperación. Intenta de nuevo.', 'error')
        return redirect(url_for('main.forgot_password'))

    crear_log_audit(
        user_id=user['user_id'],
        action='PASSWORD_RESET_REQUEST',
        resource='auth',
        details={'email': email, 'channel': 'manual_token'},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )

    if not current_app.config.get('SHOW_RESET_DEBUG_TOKEN'):
        # En producción no se muestra el token directamente por seguridad (evita account takeover).
        # El mensaje es idéntico al caso en que los datos no coinciden.
        flash('Si tus datos coinciden, se ha procesado la solicitud. Contacta a soporte si necesitas ayuda adicional.', 'success')
        return redirect(url_for('main.forgot_password'))

    flash('Token generado. Guárdalo y valídalo cuando quieras.', 'success')
    return render_template(
        'forgot_password.html',
        debug_reset=build_reset_debug_context(email, result['token'], result['expires_at']),
        email_sent=False,
    )


@main_bp.route('/validate-token')
def validate_token_page():
    """Página secundaria para validar manualmente un token recibido por correo."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))
    return render_template('validate_token.html')


@main_bp.route('/verify-token', methods=['POST'])
@limiter.limit('5 per hour', methods=['POST'])
def verify_token():
    """Valida manualmente un token y redirige al formulario final de reset."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    token = request.form.get('token', '').strip()
    if not token:
        flash('El token es requerido.', 'error')
        return redirect(url_for('main.validate_token_page'))

    token_validation = validar_reset_token(token)
    if not token_validation['valid']:
        flash(token_validation['error'], 'error')
        return redirect(url_for('main.validate_token_page'))

    user = obtener_usuario_por_id(token_validation['user_id'])
    if user is None:
        flash('No se encontró el usuario asociado.', 'error')
        return redirect(url_for('main.validate_token_page'))

    return redirect(url_for('main.reset_password_with_email', token=token, email=user.get('email', '')))


@main_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
@limiter.limit('5 per hour', methods=['POST'])
def reset_password_with_email(token):
    """Permite establecer una nueva contraseña con un token válido."""
    if session.get('user_id'):
        return redirect(url_for('main.dashboard'))

    token_validation = validar_reset_token(token)
    if not token_validation['valid']:
        flash(token_validation['error'], 'error')
        return redirect(url_for('main.forgot_password'))

    user = obtener_usuario_por_id(token_validation['user_id'])
    if not user or user.get('status') != 'active':
        flash('No se pudo procesar la solicitud para esta cuenta.', 'error')
        return redirect(url_for('main.forgot_password'))

    email = request.args.get('email', '') or (user.get('email') if user else '')

    if request.method == 'GET':
        return render_template('reset_password.html', token=token, email=email)

    password = request.form.get('password', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    errores = []
    if not validar_password(password):
        errores.append('La contraseña debe tener entre 8 y 128 caracteres e incluir al menos una letra y un número.')
    if password != confirm_password:
        errores.append('Las contraseñas no coinciden.')
    if user is None or user.get('status') != 'active':
        errores.append('No se pudo procesar la solicitud para esta cuenta.')

    if errores:
        for error in errores:
            flash(error, 'error')
        return render_template('reset_password.html', token=token, email=email)

    resultado = actualizar_password_usuario(token_validation['user_id'], generate_password_hash(password))
    if not resultado['success']:
        flash(f'No se pudo actualizar la contraseña: {resultado["error"]}', 'error')
        return render_template('reset_password.html', token=token, email=email)

    # Note: actualizar_password_usuario already handles token invalidation
    session.clear()
    crear_log_audit(
        user_id=token_validation['user_id'],
        action='PASSWORD_RESET',
        resource='auth',
        details={'email': email},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash('Tu contraseña fue actualizada. Ya puedes iniciar sesión.', 'success')
    return redirect(url_for('main.login'))


@main_bp.route('/admin')
@require_admin
def admin_panel():
    """Panel simple de administración con paginación (Optimizado: paginación en DB)."""
    page = max(1, request.args.get('page', 1, type=int))
    per_page = current_app.config['ADMIN_USERS_PER_PAGE']
    offset = (page - 1) * per_page

    usuarios = obtener_todos_usuarios(limit=per_page, offset=offset)
    total_usuarios = contar_usuarios()

    # Construcción manual de metadatos de paginación para mantener compatibilidad con la plantilla
    total_pages = max(1, math.ceil(total_usuarios / per_page)) if per_page else 1
    current_page = max(1, min(page, total_pages))
    pagination = {
        'page': current_page,
        'total_pages': total_pages,
        'has_prev': current_page > 1,
        'has_next': current_page < total_pages,
        'prev_page': current_page - 1,
        'next_page': current_page + 1,
    }

    return render_template(
        'admin.html',
        usuarios=usuarios,
        pagination=pagination,
        total_usuarios=total_usuarios,
        query_args_builder=build_query_args,
    )


@main_bp.route('/admin/collections')
@require_admin
def admin_collections():
    """Vista administrativa de colecciones públicas y privadas (Optimizado: paginación en DB)."""
    visibility = request.args.get('visibility', '').strip().lower()
    collection_filter = visibility if visibility in {'public', 'private'} else None

    page = max(1, request.args.get('page', 1, type=int))
    per_page = current_app.config['ADMIN_USERS_PER_PAGE']
    offset = (page - 1) * per_page

    collections = obtener_resumenes_colecciones(collection_filter, limit=per_page, offset=offset)
    total_collections = contar_resumenes_colecciones(collection_filter)

    total_pages = max(1, math.ceil(total_collections / per_page)) if per_page else 1
    current_page = max(1, min(page, total_pages))

    pagination = {
        'page': current_page,
        'total_pages': total_pages,
        'has_prev': current_page > 1,
        'has_next': current_page < total_pages,
        'prev_page': current_page - 1,
        'next_page': current_page + 1,
    }

    return render_template(
        'admin_collections.html',
        collections=collections,
        visibility=visibility,
        pagination=pagination,
        query_args_builder=build_query_args,
    )


@main_bp.route('/admin/delete/<user_id>', methods=['POST'])
@require_admin
@limiter.limit('10 per minute')
def admin_eliminar_usuario(user_id):
    """Elimina un usuario salvo al propio admin actual."""
    if session.get('user_id') == user_id:
        flash('No puedes eliminar tu propia cuenta desde el panel.', 'error')
        return redirect(url_for('main.admin_panel'))

    resultado = eliminar_usuario(user_id)
    if not resultado['success']:
        flash(f'No se pudo eliminar el usuario: {resultado["error"]}', 'error')
        crear_log_audit(
            user_id=session['user_id'],
            action='ADMIN_ACTION',
            resource='users',
            details={'target_user_id': user_id, 'operation': 'delete_user', 'error': resultado.get('error')},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        return redirect(url_for('main.admin_panel'))

    crear_log_audit(
        user_id=session['user_id'],
        action='ADMIN_ACTION',
        resource='users',
        details={'target_user_id': user_id, 'operation': 'delete_user'},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash('Usuario eliminado.', 'success')
    return redirect(url_for('main.admin_panel'))


@main_bp.route('/admin/edit/<user_id>', methods=['POST'])
@require_admin
@limiter.limit('10 per minute')
def admin_editar_usuario(user_id):
    """Edita el nombre principal de un usuario."""
    nuevo_nombre = request.form.get('nombre', '').strip()
    if not nuevo_nombre:
        flash('El nombre no puede estar vacío.', 'error')
        return redirect(url_for('main.admin_panel'))

    if len(nuevo_nombre) > 120:
        flash('El nombre es demasiado largo (máximo 120 caracteres).', 'error')
        return redirect(url_for('main.admin_panel'))

    resultado = actualizar_usuario_nombre(user_id, nuevo_nombre)
    if not resultado['success']:
        flash(f'No se pudo actualizar el usuario: {resultado["error"]}', 'error')
        crear_log_audit(
            user_id=session['user_id'],
            action='ADMIN_ACTION',
            resource='users',
            details={'target_user_id': user_id, 'operation': 'rename_user', 'error': resultado.get('error')},
            ip_address=request.remote_addr or 'unknown',
            user_agent=request.headers.get('User-Agent', 'unknown'),
            status='FAILED',
        )
        return redirect(url_for('main.admin_panel'))

    crear_log_audit(
        user_id=session['user_id'],
        action='ADMIN_ACTION',
        resource='users',
        details={'target_user_id': user_id, 'operation': 'rename_user'},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash('Nombre actualizado.', 'success')
    return redirect(url_for('main.admin_panel'))


@main_bp.route('/admin/logs')
@require_admin
def admin_logs():
    """Panel de logs de actividad en modo explorador por cuentas."""
    filters = {
        'user_id': request.args.get('user_id', '').strip(),
        'action': request.args.get('action', '').strip(),
        'status': request.args.get('status', '').strip(),
        'start_date': request.args.get('start_date', '').strip(),
        'end_date': request.args.get('end_date', '').strip(),
    }
    logs = obtener_todos_logs(filters, limit=500)
    page = request.args.get('page', 1, type=int)
    stats = obtener_estadisticas_logs()
    grouped_logs = build_admin_log_groups(logs)
    pagination = paginate_items(grouped_logs, page, current_app.config['ADMIN_USERS_PER_PAGE'])
    selected_user_id = request.args.get('selected_user_id', '').strip()
    selected_group = None
    if pagination['items']:
        selected_group = next(
            (group for group in pagination['items'] if group['user_id'] == selected_user_id),
            pagination['items'][0],
        )

    return render_template(
        'admin_logs.html',
        grouped_logs=pagination['items'],
        selected_group=selected_group,
        stats=stats,
        filters=filters,
        AUDIT_ACTIONS=AUDIT_ACTIONS,
        pagination=pagination,
        query_args_builder=build_query_args,
    )


@main_bp.route('/admin/logs/export')
@require_admin
@limiter.limit('5 per minute')
def admin_logs_export():
    """Exporta logs a CSV."""
    filters = {
        'user_id': request.args.get('user_id', '').strip(),
        'action': request.args.get('action', '').strip(),
        'status': request.args.get('status', '').strip(),
        'start_date': request.args.get('start_date', '').strip(),
        'end_date': request.args.get('end_date', '').strip(),
    }
    csv_content = exportar_logs_csv(obtener_todos_logs(filters, limit=1000))
    response = Response(csv_content, mimetype='text/csv')
    response.headers.set('Content-Disposition', 'attachment', filename='gamevault_audit_logs.csv')
    return response


@main_bp.route('/admin/logs/clear', methods=['POST'])
@require_admin
@limiter.limit('1 per minute')
def admin_logs_clear():
    """Limpia logs antiguos de manera manual."""
    dias = max(request.form.get('dias', 7, type=int), 1)
    resultado = limpiar_logs_antiguos(dias)
    crear_log_audit(
        user_id=session['user_id'],
        action='ADMIN_ACTION',
        resource='audit_logs',
        details={'operation': 'clear_logs', 'deleted': resultado.get('deleted', 0), 'days': dias},
        ip_address=request.remote_addr or 'unknown',
        user_agent=request.headers.get('User-Agent', 'unknown'),
        status='SUCCESS',
    )
    flash(f'Se eliminaron {resultado.get("deleted", 0)} logs antiguos.', 'success')
    return redirect(url_for('main.admin_logs'))
