"""
app/models.py - Capa de datos de GameVault sobre PostgreSQL/Neon.

La app mantiene la misma interfaz pública de funciones para no reescribir
las rutas, pero ahora persiste usuarios, juegos, tokens y logs en SQL.
"""

from __future__ import annotations

import csv
import hashlib
import io
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    case,
    create_engine,
    delete,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash


RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', 30))
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 90))
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'none').strip().lower()
LOCAL_UPLOAD_DIR = os.environ.get('LOCAL_UPLOAD_DIR', os.path.join(os.path.dirname(__file__), 'static', 'uploads'))
LOCAL_UPLOAD_URL_PATH = os.environ.get('LOCAL_UPLOAD_URL_PATH', '/static/uploads').rstrip('/')


def hash_token(token: str) -> str:
    """Genera un hash seguro para tokens de un solo uso (SHA-256)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def utcnow() -> datetime:
    """Obtiene el tiempo actual en UTC."""
    return datetime.now(timezone.utc)


def iso_now() -> str:
    """Serializa el tiempo actual en UTC."""
    return utcnow().isoformat()


def future_unix_timestamp(minutes: int = 0, days: int = 0) -> int:
    """Mantiene compatibilidad con el contrato anterior."""
    return int((utcnow() + timedelta(minutes=minutes, days=days)).timestamp())


def normalize_database_url(raw_url: str | None) -> str:
    """Convierte URLs a un formato que SQLAlchemy pueda usar."""
    if raw_url:
        if raw_url.startswith('postgresql://') and '+psycopg' not in raw_url:
            return raw_url.replace('postgresql://', 'postgresql+psycopg://', 1)
        if raw_url.startswith('postgres://'):
            return raw_url.replace('postgres://', 'postgresql+psycopg://', 1)
        return raw_url

    app_env = os.environ.get('APP_ENV', 'development').strip().lower()
    if app_env == 'testing':
        return 'sqlite+pysqlite:///gamevault_test.db'
    return 'sqlite+pysqlite:///gamevault_dev.db'


DATABASE_URL = normalize_database_url(os.environ.get('DATABASE_URL'))
_engine = None
_session_factory = None
_database_initialized = False


class Base(DeclarativeBase):
    """Base declarativa SQLAlchemy."""


class User(Base):
    __tablename__ = 'users'

    user_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    nombre: Mapped[str] = mapped_column(String(120))
    apellido: Mapped[str] = mapped_column(String(120), default='')
    prefijo_pais: Mapped[str] = mapped_column(String(10), default='')
    telefono: Mapped[str] = mapped_column(String(20), default='')
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default='user')
    status: Mapped[str] = mapped_column(String(20), default='active')
    collection_visibility: Mapped[str] = mapped_column(String(20), default='private')
    homepage_showcase_opt_in: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    games: Mapped[List['Game']] = relationship(cascade='all, delete-orphan', back_populates='user')
    reset_tokens: Mapped[List['PasswordResetToken']] = relationship(cascade='all, delete-orphan', back_populates='user')
    audit_logs: Mapped[List['AuditLog']] = relationship(cascade='all, delete-orphan', back_populates='user')


class Game(Base):
    __tablename__ = 'games'

    game_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id', ondelete='CASCADE'), index=True)
    titulo: Mapped[str] = mapped_column(String(255))
    descripcion: Mapped[str] = mapped_column(Text)
    imagen_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    plataforma: Mapped[str] = mapped_column(String(80), default='PC')
    estado: Mapped[str] = mapped_column(String(80), default='N/A')
    categoria: Mapped[str] = mapped_column(String(80), default='Biblioteca')
    prioridad: Mapped[str] = mapped_column(String(20), default='Media')
    calificacion: Mapped[int | None] = mapped_column(Integer, nullable=True)
    es_favorito: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    user: Mapped[User] = relationship(back_populates='games')


class PasswordResetToken(Base):
    __tablename__ = 'password_reset_tokens'

    token_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey('users.user_id', ondelete='CASCADE'), index=True)
    reset_token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str] = mapped_column(String(64), default='unknown')

    user: Mapped[User] = relationship(back_populates='reset_tokens')


class AuditLog(Base):
    __tablename__ = 'audit_logs'

    audit_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey('users.user_id', ondelete='SET NULL'), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    action_name: Mapped[str] = mapped_column(String(120))
    resource: Mapped[str] = mapped_column(String(80))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    ip_address: Mapped[str] = mapped_column(String(64), default='unknown')
    user_agent: Mapped[str] = mapped_column(Text, default='unknown')
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default='SUCCESS', index=True)

    user: Mapped[User | None] = relationship(back_populates='audit_logs')


class ShowcaseRating(Base):
    __tablename__ = 'showcase_ratings'

    rating_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    subject_type: Mapped[str] = mapped_column(String(20), index=True)
    subject_id: Mapped[str] = mapped_column(String(120), index=True)
    ip_address: Mapped[str] = mapped_column(String(64), index=True)
    rating: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


AUDIT_ACTIONS = {
    'LOGIN': 'Inicio de sesión',
    'LOGOUT': 'Cierre de sesión',
    'REGISTER': 'Registro de usuario',
    'CREATE_GAME': 'Crear juego',
    'UPDATE_GAME': 'Actualizar juego',
    'DELETE_GAME': 'Eliminar juego',
    'PASSWORD_RESET_REQUEST': 'Solicitud de recuperacion',
    'PASSWORD_RESET': 'Recuperación de contraseña',
    'ADMIN_ACTION': 'Acción administrativa',
    'UPDATE_PROFILE': 'Actualizar perfil',
    'CHANGE_PASSWORD': 'Cambio de contraseña',
    'FAILED_LOGIN': 'Login fallido',
}


def get_engine():
    """Obtiene el engine SQLAlchemy compartido."""
    global _engine
    if _engine is not None:
        return _engine

    kwargs: Dict[str, Any] = {'future': True, 'pool_pre_ping': True}
    if DATABASE_URL.startswith('sqlite'):
        kwargs['connect_args'] = {'check_same_thread': False}
        if ':memory:' in DATABASE_URL:
            kwargs['poolclass'] = StaticPool

    _engine = create_engine(DATABASE_URL, **kwargs)
    return _engine


def get_session_factory():
    """Obtiene la factoría de sesiones compartida."""
    global _session_factory
    if _session_factory is not None:
        return _session_factory

    _session_factory = scoped_session(
        sessionmaker(bind=get_engine(), autoflush=False, autocommit=False, expire_on_commit=False)
    )
    return _session_factory


def init_database() -> None:
    """Crea tablas si aún no existen."""
    global _database_initialized
    if not _database_initialized:
        # Movemos la comprobación de compatibilidad de esquema dentro del bloque
        # de inicialización única para evitar inspecciones costosas en cada consulta.
        Base.metadata.create_all(get_engine())
        ensure_schema_compatibility()
        _database_initialized = True


def ensure_schema_compatibility() -> None:
    """Añade columnas nuevas cuando una base existente aún no las conoce."""
    engine = get_engine()
    inspector = inspect(engine)
    default_false = 'FALSE' if engine.dialect.name == 'postgresql' else '0'
    if inspector.has_table('users'):
        user_columns = {column['name'] for column in inspector.get_columns('users')}
        user_alter_statements = []
        if 'collection_visibility' not in user_columns:
            user_alter_statements.append("ALTER TABLE users ADD COLUMN collection_visibility VARCHAR(20) DEFAULT 'private'")
        if 'homepage_showcase_opt_in' not in user_columns:
            user_alter_statements.append(f"ALTER TABLE users ADD COLUMN homepage_showcase_opt_in BOOLEAN DEFAULT {default_false}")
        if user_alter_statements:
            with engine.begin() as connection:
                for statement in user_alter_statements:
                    connection.execute(text(statement))
                connection.execute(
                    text("UPDATE users SET collection_visibility = 'private' WHERE collection_visibility IS NULL OR collection_visibility = ''")
                )
                connection.execute(
                    text(f'UPDATE users SET homepage_showcase_opt_in = {default_false} WHERE homepage_showcase_opt_in IS NULL')
                )

    if not inspector.has_table('games'):
        return

    columns = {column['name'] for column in inspector.get_columns('games')}
    alter_statements = []

    if 'categoria' not in columns:
        alter_statements.append("ALTER TABLE games ADD COLUMN categoria VARCHAR(80) DEFAULT 'Biblioteca'")
    if 'prioridad' not in columns:
        alter_statements.append("ALTER TABLE games ADD COLUMN prioridad VARCHAR(20) DEFAULT 'Media'")
    if 'calificacion' not in columns:
        alter_statements.append("ALTER TABLE games ADD COLUMN calificacion INTEGER")
    if 'es_favorito' not in columns:
        alter_statements.append(f"ALTER TABLE games ADD COLUMN es_favorito BOOLEAN DEFAULT {default_false}")

    if not alter_statements:
        return

    with engine.begin() as connection:
        for statement in alter_statements:
            connection.execute(text(statement))
        connection.execute(text("UPDATE games SET categoria = 'Biblioteca' WHERE categoria IS NULL OR categoria = ''"))
        connection.execute(text("UPDATE games SET prioridad = 'Media' WHERE prioridad IS NULL OR prioridad = ''"))
        connection.execute(text(f'UPDATE games SET es_favorito = {default_false} WHERE es_favorito IS NULL'))


def database_healthcheck() -> bool:
    """Confirma que la base de datos responde."""
    try:
        init_database()
        session_factory = get_session_factory()
        with session_factory() as session:
            session.execute(select(1))
        return True
    except Exception:
        return False


def ensure_tables() -> None:
    """Garantiza el esquema antes de operar."""
    init_database()


def _as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def user_to_dict(user: User | None) -> Optional[Dict[str, Any]]:
    if user is None:
        return None
    return {
        'user_id': user.user_id,
        'email': user.email,
        'nombre': user.nombre,
        'apellido': user.apellido,
        'prefijo_pais': user.prefijo_pais,
        'telefono': user.telefono,
        'password_hash': user.password_hash,
        'role': user.role,
        'status': user.status,
        'collection_visibility': user.collection_visibility,
        'homepage_showcase_opt_in': user.homepage_showcase_opt_in,
        'created_at': _as_iso(user.created_at),
        'updated_at': _as_iso(user.updated_at),
    }


def game_to_dict(game: Game | None) -> Optional[Dict[str, Any]]:
    if game is None:
        return None
    return {
        'game_id': game.game_id,
        'user_id': game.user_id,
        'titulo': game.titulo,
        'descripcion': game.descripcion,
        'imagen_url': game.imagen_url,
        'plataforma': game.plataforma,
        'estado': game.estado,
        'categoria': game.categoria,
        'prioridad': game.prioridad,
        'calificacion': game.calificacion,
        'es_favorito': game.es_favorito,
        'created_at': _as_iso(game.created_at),
        'updated_at': _as_iso(game.updated_at),
    }


def reset_token_to_dict(item: PasswordResetToken | None) -> Optional[Dict[str, Any]]:
    if item is None:
        return None
    return {
        'token_id': item.token_id,
        'user_id': item.user_id,
        'reset_token': item.reset_token,
        'created_at': _as_iso(item.created_at),
        'expires_at': _as_iso(item.expires_at),
        'expires_at_unix': int(item.expires_at.timestamp()),
        'used': item.used,
        'used_at': _as_iso(item.used_at),
        'ip_address': item.ip_address,
    }


def audit_log_to_dict(item: AuditLog | None) -> Optional[Dict[str, Any]]:
    if item is None:
        return None
    return {
        'audit_id': item.audit_id,
        'user_id': item.user_id,
        'action': item.action,
        'action_name': item.action_name,
        'resource': item.resource,
        'timestamp': _as_iso(item.timestamp),
        'ip_address': item.ip_address,
        'user_agent': item.user_agent,
        'details': item.details or {},
        'status': item.status,
    }


def parse_date_filter(value: str, *, end: bool = False) -> Optional[datetime]:
    """Convierte filtros de fecha simple a datetime UTC."""
    if not value:
        return None
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if end:
        parsed = parsed + timedelta(days=1)
    return parsed


def validar_email(email):
    """Valida el formato y longitud del email (max 255)."""
    if not email or len(email) > 255:
        return False
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None


def validar_telefono(telefono):
    """Valida que el teléfono contenga solo dígitos y tenga longitud válida (7-20)."""
    return telefono.isdigit() and 7 <= len(telefono) <= 20


def validar_password(password):
    """Valida que la contraseña tenga una longitud segura (8-128)."""
    # El límite superior de 128 protege contra ataques DoS al algoritmo de hashing.
    return 8 <= len(password) <= 128


def eliminar_imagen_s3(imagen_url):
    """Compatibilidad temporal mientras el storage nuevo queda pendiente."""
    if STORAGE_BACKEND == 'local' and imagen_url and imagen_url.startswith(LOCAL_UPLOAD_URL_PATH + '/'):
        relative_path = imagen_url.replace(LOCAL_UPLOAD_URL_PATH + '/', '', 1).lstrip('/')
        destination = os.path.abspath(os.path.join(LOCAL_UPLOAD_DIR, relative_path))
        upload_root = os.path.abspath(LOCAL_UPLOAD_DIR)
        if destination.startswith(upload_root) and os.path.exists(destination):
            os.remove(destination)
    return True


def obtener_key_desde_url(imagen_url):
    """Compatibilidad temporal para futuras integraciones de storage."""
    return imagen_url


def crear_url_firmada_lectura(imagen_url: str, expires_in: int = 3600) -> str:
    """Por ahora devuelve la URL tal cual o vacío si no hay imagen."""
    return imagen_url or ''


def crear_juego(
    user_id,
    game_id,
    titulo,
    descripcion,
    imagen_url,
    plataforma='PC',
    estado='N/A',
    categoria='Biblioteca',
    prioridad='Media',
    calificacion=None,
    es_favorito=False,
):
    """Guarda un juego para un usuario."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        game = Game(
            game_id=game_id,
            user_id=user_id,
            titulo=titulo.strip(),
            descripcion=descripcion.strip(),
            imagen_url=(imagen_url or '').strip() or None,
            plataforma=plataforma,
            estado=estado,
            categoria=(categoria or 'Biblioteca').strip(),
            prioridad=(prioridad or 'Media').strip(),
            calificacion=calificacion,
            es_favorito=bool(es_favorito),
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        session.add(game)
        session.commit()
        return game_to_dict(game)


def obtener_juegos_por_usuario(user_id):
    """Obtiene todos los juegos de un usuario."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        items = session.scalars(
            select(Game).where(Game.user_id == user_id).order_by(Game.updated_at.desc(), Game.created_at.desc())
        ).all()
        return [game_to_dict(item) for item in items]


def obtener_juego_por_id(user_id, game_id):
    """Obtiene un juego por ID y usuario."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        item = session.scalar(select(Game).where(Game.user_id == user_id, Game.game_id == game_id))
        return game_to_dict(item)


def eliminar_juego(user_id, game_id):
    """Elimina un juego del usuario."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        game = session.scalar(select(Game).where(Game.user_id == user_id, Game.game_id == game_id))
        if game is None:
            return {'success': False, 'juego': None, 'error': 'Juego no encontrado'}
        juego_dict = game_to_dict(game)
        eliminar_imagen_s3(game.imagen_url)
        session.delete(game)
        session.commit()
        return {'success': True, 'juego': juego_dict, 's3_eliminada': True}


def actualizar_juego(user_id, game_id, nuevos_datos, nueva_imagen=None):
    """Actualiza un juego existente."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        game = session.scalar(select(Game).where(Game.user_id == user_id, Game.game_id == game_id))
        if game is None:
            return {'success': False, 'juego': None, 'error': 'Juego no encontrado'}

        if nuevos_datos.get('titulo'):
            game.titulo = nuevos_datos['titulo'].strip()
        if nuevos_datos.get('descripcion'):
            game.descripcion = nuevos_datos['descripcion'].strip()
        if 'plataforma' in nuevos_datos:
            game.plataforma = nuevos_datos['plataforma']
        if 'estado' in nuevos_datos:
            game.estado = nuevos_datos['estado']
        if 'categoria' in nuevos_datos:
            game.categoria = nuevos_datos['categoria']
        if 'prioridad' in nuevos_datos:
            game.prioridad = nuevos_datos['prioridad']
        if 'calificacion' in nuevos_datos:
            game.calificacion = nuevos_datos['calificacion']
        if 'es_favorito' in nuevos_datos:
            game.es_favorito = bool(nuevos_datos['es_favorito'])

        if isinstance(nueva_imagen, str):
            if game.imagen_url and game.imagen_url != nueva_imagen:
                eliminar_imagen_s3(game.imagen_url)
            game.imagen_url = nueva_imagen.strip() or None
        elif nueva_imagen:
            from app.routes import subir_imagen_a_s3

            uploaded_url = subir_imagen_a_s3(nueva_imagen)
            if uploaded_url is None:
                return {'success': False, 'juego': None, 'error': 'Error al subir nueva imagen'}
            eliminar_imagen_s3(game.imagen_url)
            game.imagen_url = uploaded_url

        game.updated_at = utcnow()
        session.commit()
        session.refresh(game)
        return {'success': True, 'juego': game_to_dict(game), 'error': None}


def crear_usuario(nombre, apellido, email, prefijo_pais, telefono, password_hash):
    """Crea un usuario nuevo."""
    ensure_tables()
    session_factory = get_session_factory()
    email_normalizado = email.lower().strip()
    user = User(
        user_id=str(uuid.uuid4()),
        email=email_normalizado,
        nombre=nombre.strip(),
        apellido=(apellido or '').strip(),
        prefijo_pais=(prefijo_pais or '').strip(),
        telefono=(telefono or '').strip(),
        password_hash=password_hash,
        role='user',
        status='active',
        collection_visibility='private',
        homepage_showcase_opt_in=False,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    try:
        with session_factory() as session:
            session.add(user)
            session.commit()
            session.refresh(user)
            return user_to_dict(user)
    except IntegrityError:
        return None


def obtener_usuario_por_email(email):
    """Obtiene un usuario por email."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == email.lower().strip()))
        return user_to_dict(user)


def verificar_credenciales(email, password):
    """Compatibilidad con la interfaz previa."""
    return obtener_usuario_por_email(email)


def obtener_todos_usuarios(limit: int | None = None, offset: int | None = None) -> List[Dict[str, Any]]:
    """Obtiene todos los usuarios (ahora con soporte para paginación en DB)."""
    ensure_tables()
    session_factory = get_session_factory()
    query = select(User).order_by(User.created_at.desc())
    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    with session_factory() as session:
        items = session.scalars(query).all()
        return [user_to_dict(item) for item in items]


def contar_usuarios() -> int:
    """Retorna el conteo total de usuarios en la base de datos."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        return session.scalar(select(func.count(User.user_id))) or 0


def eliminar_usuario(user_id):
    """Elimina un usuario y sus relaciones."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            return {'success': False, 'error': 'Usuario no encontrado'}
        session.delete(user)
        session.commit()
        return {'success': True, 'error': None}


def actualizar_usuario_nombre(user_id, nombre):
    """Actualiza el nombre principal de un usuario."""
    return actualizar_usuario_perfil(user_id, {'nombre': nombre.strip()})


def crear_reset_token(user_id: str, ip_address: str = None) -> Dict[str, Any]:
    """Crea un token de recuperación de contraseña."""
    ensure_tables()
    session_factory = get_session_factory()
    now = utcnow()
    expires_at = now + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
    raw_token = secrets.token_urlsafe(32)
    item = PasswordResetToken(
        token_id=str(uuid.uuid4()),
        user_id=user_id,
        reset_token=hash_token(raw_token),
        created_at=now,
        expires_at=expires_at,
        used=False,
        ip_address=ip_address or 'unknown',
    )
    with session_factory() as session:
        session.add(item)
        session.commit()
        return {
            'success': True,
            'token': raw_token,
            'expires_at': expires_at,
            'error': None,
        }


def obtener_token_por_valor(reset_token: str, only_active: bool = True) -> List[Dict[str, Any]]:
    """Busca tokens por valor."""
    ensure_tables()
    session_factory = get_session_factory()
    hashed = hash_token(reset_token)
    with session_factory() as session:
        query = select(PasswordResetToken).where(PasswordResetToken.reset_token == hashed)
        if only_active:
            query = query.where(
                PasswordResetToken.used.is_(False),
                PasswordResetToken.expires_at > utcnow(),
            )
        items = session.scalars(query.order_by(PasswordResetToken.created_at.desc())).all()
        return [reset_token_to_dict(item) for item in items]


def validar_reset_token(reset_token: str) -> Dict[str, Any]:
    """Valida un token de recuperación."""
    items = obtener_token_por_valor(reset_token, only_active=True)
    if not items:
        return {'valid': False, 'user_id': None, 'error': 'Token no encontrado o ya utilizado'}

    item = items[0]
    expires_at = datetime.fromisoformat(item['expires_at'])
    if expires_at < utcnow():
        return {'valid': False, 'user_id': None, 'error': 'Token expirado'}

    return {'valid': True, 'user_id': item['user_id'], 'error': None}


def usar_token(reset_token: str) -> Dict[str, Any]:
    """Marca un token como usado."""
    ensure_tables()
    session_factory = get_session_factory()
    hashed = hash_token(reset_token)
    with session_factory() as session:
        item = session.scalar(select(PasswordResetToken).where(PasswordResetToken.reset_token == hashed))
        if item is None:
            return {'success': False, 'error': 'Token no encontrado'}
        item.used = True
        item.used_at = utcnow()
        session.commit()
        return {'success': True, 'error': None}


def obtener_token_por_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene el token activo más reciente de un usuario."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        item = session.scalar(
            select(PasswordResetToken)
            .where(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.used.is_(False),
                PasswordResetToken.expires_at > utcnow(),
            )
            .order_by(PasswordResetToken.created_at.desc())
        )
        return reset_token_to_dict(item)


def eliminar_tokens_expirados() -> Dict[str, Any]:
    """Elimina tokens expirados (optimizado con batch delete)."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        stmt = delete(PasswordResetToken).where(
            PasswordResetToken.used.is_(False),
            PasswordResetToken.expires_at < utcnow(),
        )
        result = session.execute(stmt)
        deleted = result.rowcount
        session.commit()
        return {'deleted': deleted, 'error': None}


def crear_log_audit(
    user_id: str,
    action: str,
    resource: str,
    details: Dict[str, Any] = None,
    ip_address: str = None,
    user_agent: str = None,
    status: str = 'SUCCESS',
) -> Dict[str, Any]:
    """Crea un log de auditoría."""
    ensure_tables()
    session_factory = get_session_factory()
    item = AuditLog(
        audit_id=str(uuid.uuid4()),
        user_id=user_id,
        action=action,
        action_name=AUDIT_ACTIONS.get(action, action),
        resource=resource,
        timestamp=utcnow(),
        ip_address=ip_address or 'unknown',
        user_agent=user_agent or 'unknown',
        details=details or {},
        status=status,
    )
    with session_factory() as session:
        session.add(item)
        session.commit()
        return {'success': True, 'audit_id': item.audit_id, 'error': None}


def obtener_logs_por_usuario(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Obtiene logs recientes de un usuario."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        items = session.scalars(
            select(AuditLog).where(AuditLog.user_id == user_id).order_by(AuditLog.timestamp.desc()).limit(limit)
        ).all()
        return [audit_log_to_dict(item) for item in items]


def obtener_todos_logs(filters: Dict[str, Any] = None, limit: int = 100) -> List[Dict[str, Any]]:
    """Obtiene logs de auditoría con filtros opcionales."""
    ensure_tables()
    session_factory = get_session_factory()
    filters = filters or {}

    query = select(AuditLog)
    if filters.get('user_id'):
        query = query.where(AuditLog.user_id == filters['user_id'])
    if filters.get('action'):
        query = query.where(AuditLog.action == filters['action'])
    if filters.get('status'):
        query = query.where(AuditLog.status == filters['status'])

    start_date = parse_date_filter(filters.get('start_date', ''))
    end_date = parse_date_filter(filters.get('end_date', ''), end=True)
    if start_date:
        query = query.where(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.where(AuditLog.timestamp < end_date)

    query = query.order_by(AuditLog.timestamp.desc()).limit(limit)

    with session_factory() as session:
        items = session.scalars(query).all()
        return [audit_log_to_dict(item) for item in items]


def obtener_estadisticas_logs() -> Dict[str, Any]:
    """Calcula estadísticas simples de auditoría usando agregaciones en base de datos."""
    ensure_tables()
    session_factory = get_session_factory()
    now = utcnow()

    with session_factory() as session:
        # 1. Total logs
        total_logs = session.scalar(select(func.count(AuditLog.audit_id))) or 0

        if total_logs == 0:
            return {
                'total_logs': 0,
                'action_counts': {},
                'status_counts': {},
                'daily_activity': [
                    {'date': (now - timedelta(days=i)).strftime('%Y-%m-%d'), 'count': 0}
                    for i in range(6, -1, -1)
                ],
                'top_users': [],
                'success_rate': 100.0,
            }

        # 2. Action counts
        action_results = session.execute(
            select(AuditLog.action, func.count(AuditLog.audit_id)).group_by(AuditLog.action)
        ).all()
        action_counts = {row[0]: row[1] for row in action_results}

        # 3. Status counts
        status_results = session.execute(
            select(AuditLog.status, func.count(AuditLog.audit_id)).group_by(AuditLog.status)
        ).all()
        status_counts = {row[0]: row[1] for row in status_results}

        # 4. Top users
        user_results = session.execute(
            select(AuditLog.user_id, func.count(AuditLog.audit_id))
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.audit_id).desc())
            .limit(5)
        ).all()
        top_users = [(row[0] or 'anonymous', row[1]) for row in user_results]

        # 5. Daily activity (last 7 days)
        cutoff = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=6)

        # Portable grouping by date (YYYY-MM-DD)
        daily_results = session.execute(
            select(func.date(AuditLog.timestamp), func.count(AuditLog.audit_id))
            .where(AuditLog.timestamp >= cutoff)
            .group_by(func.date(AuditLog.timestamp))
        ).all()

        daily_map = {str(row[0]): row[1] for row in daily_results}

        last_7_days = []
        for i in range(7):
            date_str = (now - timedelta(days=6 - i)).strftime('%Y-%m-%d')
            last_7_days.append({'date': date_str, 'count': daily_map.get(date_str, 0)})

        success_count = status_counts.get('SUCCESS', 0)
        success_rate = round((success_count / total_logs * 100), 2)

        return {
            'total_logs': total_logs,
            'action_counts': action_counts,
            'status_counts': status_counts,
            'daily_activity': last_7_days,
            'top_users': top_users,
            'success_rate': success_rate,
        }


def limpiar_logs_antiguos(days: int = None) -> Dict[str, Any]:
    """Elimina logs antiguos (optimizado con batch delete)."""
    ensure_tables()
    days = days or AUDIT_LOG_RETENTION_DAYS
    cutoff_date = utcnow() - timedelta(days=days)
    session_factory = get_session_factory()
    with session_factory() as session:
        stmt = delete(AuditLog).where(AuditLog.timestamp < cutoff_date)
        result = session.execute(stmt)
        deleted = result.rowcount
        session.commit()
        return {'deleted': deleted, 'error': None}


def exportar_logs_csv(logs: List[Dict[str, Any]]) -> str:
    """Exporta logs a CSV con protección contra CSV Injection."""
    output = io.StringIO()
    fieldnames = ['audit_id', 'user_id', 'action', 'resource', 'timestamp', 'ip_address', 'status', 'details']
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    risky_chars = ('=', '+', '-', '@', '|')

    for log in logs:
        row = {}
        for key in fieldnames[:-1]:
            val = str(log.get(key, '') or '')
            if val.startswith(risky_chars):
                val = "'" + val
            row[key] = val

        details_val = str(log.get('details', {}) or '{}')
        if details_val.startswith(risky_chars):
            details_val = "'" + details_val
        row['details'] = details_val

        writer.writerow(row)
    return output.getvalue()


def obtener_usuario_por_id(user_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por ID."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, user_id)
        return user_to_dict(user)


def obtener_usuarios_por_ids(user_ids: List[str]) -> List[Dict[str, Any]]:
    """Obtiene múltiples usuarios por sus IDs en una sola consulta."""
    if not user_ids:
        return []
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        items = session.scalars(
            select(User).where(User.user_id.in_(user_ids))
        ).all()
        return [user_to_dict(item) for item in items]


def actualizar_usuario_perfil(user_id: str, cambios: Dict[str, str]) -> Dict[str, Any]:
    """Actualiza datos básicos del perfil."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            return {'success': False, 'error': 'Usuario no encontrado'}

        for field in ('nombre', 'apellido', 'prefijo_pais', 'telefono'):
            if field in cambios:
                setattr(user, field, (cambios.get(field) or '').strip())
        if 'collection_visibility' in cambios:
            visibility = (cambios.get('collection_visibility') or 'private').strip().lower()
            user.collection_visibility = visibility if visibility in {'private', 'public'} else 'private'
        if 'homepage_showcase_opt_in' in cambios:
            user.homepage_showcase_opt_in = bool(cambios.get('homepage_showcase_opt_in'))
        user.updated_at = utcnow()
        session.commit()
        return {'success': True, 'error': None}


def actualizar_password_usuario(user_id: str, password_hash: str) -> Dict[str, Any]:
    """Actualiza la contraseña del usuario e invalida tokens de recuperación previos."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            return {'success': False, 'error': 'Usuario no encontrado'}

        # Invalidate all active reset tokens for this user after a password change (Security enhancement)
        session.execute(delete(PasswordResetToken).where(PasswordResetToken.user_id == user_id))

        user.password_hash = password_hash
        user.updated_at = utcnow()
        session.commit()
        return {'success': True, 'error': None}


def obtener_resumenes_colecciones(
    visibility: str | None = None,
    limit: int | None = None,
    homepage_only: bool = False,
) -> List[Dict[str, Any]]:
    """Obtiene resúmenes de colecciones de usuarios (optimizado con agregación en SQL)."""
    ensure_tables()
    session_factory = get_session_factory()

    # Subquery para métricas de juegos
    game_metrics = (
        select(
            Game.user_id,
            func.count(Game.game_id).label('total_games'),
            func.sum(case((Game.es_favorito.is_(True), 1), else_=0)).label('favorites_count'),
            func.avg(Game.calificacion).label('average_rating'),
            func.max(func.coalesce(Game.updated_at, Game.created_at)).label('last_updated_at'),
        )
        .group_by(Game.user_id)
        .subquery()
    )

    with session_factory() as session:
        # Query principal uniendo User con el resumen de sus juegos
        query = select(
            User.user_id,
            User.nombre,
            User.email,
            User.collection_visibility,
            User.homepage_showcase_opt_in,
            func.coalesce(game_metrics.c.total_games, 0).label('total_games'),
            func.coalesce(game_metrics.c.favorites_count, 0).label('favorites_count'),
            game_metrics.c.average_rating,
            game_metrics.c.last_updated_at,
        ).outerjoin(game_metrics, User.user_id == game_metrics.c.user_id)

        if visibility:
            query = query.where(User.collection_visibility == visibility)
        if homepage_only:
            query = query.where(User.homepage_showcase_opt_in.is_(True), game_metrics.c.total_games > 0)

        # Ordenamiento en SQL: Rating desc, Favoritos desc, Total desc, Actualización desc
        query = query.order_by(
            func.coalesce(game_metrics.c.average_rating, -1).desc(),
            func.coalesce(game_metrics.c.favorites_count, 0).desc(),
            func.coalesce(game_metrics.c.total_games, 0).desc(),
            game_metrics.c.last_updated_at.desc(),
        )

        if limit:
            query = query.limit(limit)

        results = session.execute(query).all()
        if not results:
            return []

        user_ids = [r.user_id for r in results]

        # Batch query para plataformas dominantes (evita N+1 y cargar todos los juegos en memoria)
        platform_query = (
            select(Game.user_id, Game.plataforma, func.count(Game.plataforma))
            .where(Game.user_id.in_(user_ids))
            .group_by(Game.user_id, Game.plataforma)
            .order_by(Game.user_id, func.count(Game.plataforma).desc())
        )
        platform_results = session.execute(platform_query).all()

        dominant_platforms = {}
        for row in platform_results:
            if row[0] not in dominant_platforms:
                dominant_platforms[row[0]] = row[1] or 'Sin plataforma'

        summaries = []
        for r in results:
            summaries.append(
                {
                    'user_id': r.user_id,
                    'owner_name': r.nombre or 'Coleccionista',
                    'owner_email': r.email,
                    'collection_visibility': r.collection_visibility,
                    'homepage_showcase_opt_in': bool(r.homepage_showcase_opt_in),
                    'total_games': int(r.total_games),
                    'favorites_count': int(r.favorites_count),
                    'average_rating': round(float(r.average_rating), 1) if r.average_rating is not None else None,
                    'dominant_platform': dominant_platforms.get(r.user_id, 'Sin juegos'),
                    'last_updated_at': _as_iso(r.last_updated_at) or '',
                }
            )

        return summaries


def obtener_colecciones_publicas(limit: int = 6) -> List[Dict[str, Any]]:
    """Devuelve colecciones públicas con algo real que mostrar (ahora optimizado)."""
    return obtener_resumenes_colecciones(visibility='public', limit=limit, homepage_only=True)


def obtener_rating_showcase(subject_type: str, subject_id: str) -> Dict[str, Any]:
    """Obtiene la valoración pública actual de un showcase mediante agregación en DB."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        result = session.execute(
            select(func.avg(ShowcaseRating.rating), func.count(ShowcaseRating.rating)).where(
                ShowcaseRating.subject_type == subject_type,
                ShowcaseRating.subject_id == subject_id,
            )
        ).first()

        if not result or result[1] == 0:
            return {'average': None, 'votes_count': 0}

        return {'average': round(float(result[0]), 1), 'votes_count': int(result[1])}


def obtener_ratings_multiple(subject_type: str, subject_ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Obtiene valoraciones para múltiples IDs en una sola consulta (evita N+1)."""
    if not subject_ids:
        return {}

    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        results = session.execute(
            select(
                ShowcaseRating.subject_id,
                func.avg(ShowcaseRating.rating),
                func.count(ShowcaseRating.rating),
            )
            .where(
                ShowcaseRating.subject_type == subject_type,
                ShowcaseRating.subject_id.in_(subject_ids),
            )
            .group_by(ShowcaseRating.subject_id)
        ).all()

        mapped = {}
        for row in results:
            mapped[str(row[0])] = {
                'average': round(float(row[1]), 1) if row[1] is not None else None,
                'votes_count': int(row[2]),
            }
        return mapped


def combinar_rating_showcase(
    summary: Dict[str, Any],
    *,
    base_average: float | int | None = None,
    base_votes_count: int = 0,
) -> Dict[str, Any]:
    """Combina una valoración persistida con un baseline visual cuando aplica."""
    actual_average = summary.get('average')
    actual_votes_count = int(summary.get('votes_count') or 0)
    base_votes_count = int(base_votes_count or 0)

    if base_average is None or base_votes_count <= 0:
        return {
            'average': actual_average,
            'votes_count': actual_votes_count,
        }

    if actual_average is None or actual_votes_count <= 0:
        return {
            'average': round(float(base_average), 1),
            'votes_count': base_votes_count,
        }

    merged_votes = base_votes_count + actual_votes_count
    merged_average = round(
        ((float(base_average) * base_votes_count) + (float(actual_average) * actual_votes_count)) / merged_votes,
        1,
    )
    return {
        'average': merged_average,
        'votes_count': merged_votes,
    }


def aplicar_ratings_showcase(
    items: List[Dict[str, Any]],
    *,
    subject_type: str,
    subject_id_key: str,
    default_rating_key: str | None = None,
    default_votes_key: str | None = None,
) -> List[Dict[str, Any]]:
    """Enriquece colecciones con valoración pública en batch para evitar N+1 queries."""
    if not items:
        return []

    subject_ids = [str(item[subject_id_key]) for item in items]
    ratings_map = obtener_ratings_multiple(subject_type, subject_ids)

    enriched: List[Dict[str, Any]] = []
    for item in items:
        entry = dict(item)
        subject_id = str(entry[subject_id_key])
        actual_rating = ratings_map.get(subject_id, {'average': None, 'votes_count': 0})

        rating_summary = combinar_rating_showcase(
            actual_rating,
            base_average=entry.get(default_rating_key) if default_rating_key else None,
            base_votes_count=entry.get(default_votes_key, 0) if default_votes_key else 0,
        )
        entry['showcase_rating_average'] = rating_summary['average']
        entry['showcase_votes_count'] = rating_summary['votes_count']
        enriched.append(entry)
    return enriched


def registrar_rating_showcase(subject_type: str, subject_id: str, rating: int, ip_address: str) -> Dict[str, Any]:
    """Guarda una valoración pública, una por IP y colección."""
    ensure_tables()
    if rating not in {1, 2, 3, 4, 5}:
        return {'success': False, 'duplicate': False, 'error': 'La valoración debe estar entre 1 y 5.'}

    session_factory = get_session_factory()
    with session_factory() as session:
        existing = session.scalar(
            select(ShowcaseRating).where(
                ShowcaseRating.subject_type == subject_type,
                ShowcaseRating.subject_id == subject_id,
                ShowcaseRating.ip_address == (ip_address or 'unknown'),
            )
        )
        if existing is not None:
            summary = obtener_rating_showcase(subject_type, subject_id)
            return {
                'success': False,
                'duplicate': True,
                'error': 'Esta IP ya valoró esta colección.',
                'average': summary['average'],
                'votes_count': summary['votes_count'],
            }

        entry = ShowcaseRating(
            rating_id=str(uuid.uuid4()),
            subject_type=subject_type,
            subject_id=subject_id,
            ip_address=ip_address or 'unknown',
            rating=rating,
            created_at=utcnow(),
        )
        session.add(entry)
        session.commit()

    summary = obtener_rating_showcase(subject_type, subject_id)
    return {
        'success': True,
        'duplicate': False,
        'error': None,
        'average': summary['average'],
        'votes_count': summary['votes_count'],
    }


def crear_presigned_upload(nombre_archivo: str, content_type: str, max_upload_bytes: int) -> Dict[str, Any]:
    """Storage nuevo pendiente: por ahora no se generan cargas firmadas."""
    raise RuntimeError('El almacenamiento de imágenes aún no está configurado.')


def ensure_bootstrap_admin(email: str, password: str, nombre: str = 'GameVault', apellido: str = 'Admin') -> Dict[str, Any]:
    """Garantiza que exista un administrador inicial para desarrollo o bootstrap controlado."""
    ensure_tables()
    if not email or not password:
        return {'success': False, 'created': False, 'updated': False, 'error': 'Faltan credenciales de bootstrap'}

    session_factory = get_session_factory()
    email_normalizado = email.lower().strip()
    with session_factory() as session:
        user = session.scalar(select(User).where(User.email == email_normalizado))
        if user is None:
            user = User(
                user_id=str(uuid.uuid4()),
                email=email_normalizado,
                nombre=(nombre or 'GameVault').strip(),
                apellido=(apellido or 'Admin').strip(),
                prefijo_pais='',
                telefono='',
                password_hash=generate_password_hash(password),
                role='admin',
                status='active',
                collection_visibility='private',
                homepage_showcase_opt_in=False,
                created_at=utcnow(),
                updated_at=utcnow(),
            )
            session.add(user)
            session.commit()
            return {'success': True, 'created': True, 'updated': False, 'error': None}

        changed = False
        user.password_hash = generate_password_hash(password)
        changed = True
        if user.role != 'admin':
            user.role = 'admin'
            changed = True
        if user.status != 'active':
            user.status = 'active'
            changed = True
        if nombre and user.nombre != nombre.strip():
            user.nombre = nombre.strip()
            changed = True
        if apellido and user.apellido != apellido.strip():
            user.apellido = apellido.strip()
            changed = True

        if changed:
            user.updated_at = utcnow()
            session.commit()
        return {'success': True, 'created': False, 'updated': changed, 'error': None}
