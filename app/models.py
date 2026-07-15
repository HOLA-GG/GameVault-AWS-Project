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
from urllib.parse import quote, unquote, urlparse

from flask import current_app
from werkzeug.utils import secure_filename
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    case,
    create_engine,
    delete,
    event,
    func,
    inspect,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash


RESET_TOKEN_EXPIRY_MINUTES = int(os.environ.get('RESET_TOKEN_EXPIRY_MINUTES', 30))
AUDIT_LOG_RETENTION_DAYS = int(os.environ.get('AUDIT_LOG_RETENTION_DAYS', 90))
STORAGE_BACKEND = os.environ.get('STORAGE_BACKEND', 'none').strip().lower()
LOCAL_UPLOAD_DIR = os.environ.get('LOCAL_UPLOAD_DIR', os.path.join(os.path.dirname(__file__), 'static', 'uploads'))
LOCAL_UPLOAD_URL_PATH = os.environ.get('LOCAL_UPLOAD_URL_PATH', '/static/uploads').rstrip('/')

# Bolt Optimization: Pre-compiled regex and constants to reduce hot-path allocations.
_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
_SENSITIVE_PATTERNS = {
    'password', 'token', 'secret', 'key', 'hash', 'auth', 'credential',
    'cookie', 'session', 'jwt', 'api', 'signature', 'private',
    'salt', 'otp', 'mfa', '2fa', 'certificate', 'nonce',
    'cvv', 'cvc', 'credit', 'card', 'ssn', 'dni', 'passport', 'iban',
    'account_number', 'tax_id', 'phone', 'telefono', 'celular', 'mobile',
    'address', 'direccion', 'birth', 'nacimiento', 'pin', 'apikey',
    'recovery', 'security', 'identity', 'national_id', 'personal_id',
    'tarjeta', 'clave', 'cuenta', 'identidad', 'expiry', 'expiration',
    'pass', 'pwd', 'sid', 'csrf', 'xsrf', 'access_token', 'refresh_token',
    'id_token', 'authorization', 'bearer', 'nif', 'nie', 'curp'
}
_RISKY_CSV_CHARS = ('=', '+', '-', '@', '|', '`')
_COMMON_WEAK_PASSWORDS = {
    'password123', 'admin123', 'admin1234', 'admin12345', 'gamer123',
    'videogames123', 'qwerty123', '12345678a', 'password1234', 'welcome123'
}


def hash_token(token: str) -> str:
    """Genera un hash seguro para tokens de un solo uso (SHA-256)."""
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def utcnow() -> datetime:
    """Obtiene el tiempo actual en UTC."""
    return datetime.now(timezone.utc)


# Bolt Optimization: Constant for safe date comparisons.
MIN_DATE = datetime(1, 1, 1, tzinfo=timezone.utc)


def iso_now() -> str:
    """Serializa el tiempo actual en UTC."""
    return utcnow().isoformat()


def future_unix_timestamp(minutes: int = 0, days: int = 0) -> int:
    """Mantiene compatibilidad con el contrato anterior."""
    return int((utcnow() + timedelta(minutes=minutes, days=days)).timestamp())


def normalize_database_url(raw_url: str | None) -> str:
    """Convierte URLs a un formato que SQLAlchemy pueda usar."""
    if raw_url:
        # Reemplazar postgres:// por postgresql+psycopg:// para compatibilidad con SQLAlchemy 2.0+
        if raw_url.startswith('postgres://'):
            raw_url = raw_url.replace('postgres://', 'postgresql+psycopg://', 1)
        elif raw_url.startswith('postgresql://') and '+psycopg' not in raw_url:
            raw_url = raw_url.replace('postgresql://', 'postgresql+psycopg://', 1)

        # Forzar sslmode=require para conexiones Neon/PostgreSQL si no se especifica
        if 'postgresql' in raw_url and 'sslmode=' not in raw_url:
            separator = '&' if '?' in raw_url else '?'
            raw_url += f"{separator}sslmode=require"

        return raw_url

    app_env = os.environ.get('APP_ENV', 'development').strip().lower()
    if app_env == 'testing':
        return 'sqlite+pysqlite:///gamevault_test.db'
    return 'sqlite+pysqlite:///gamevault_dev.db'


DATABASE_URL = normalize_database_url(os.environ.get('DATABASE_URL'))
_engine = None
_session_factory = None
_database_initialized = False

# Bolt Optimization: Module-level constants and singletons for hot-path efficiency.
_S3_CLIENT = None
ALLOWED_IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'webp', 'gif'}
ALLOWED_IMAGE_MIME_TYPES = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'image/gif',
}


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
    collection_visibility: Mapped[str] = mapped_column(String(20), default='private', index=True)
    homepage_showcase_opt_in: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True)

    games: Mapped[List['Game']] = relationship(cascade='all, delete-orphan', back_populates='user')
    reset_tokens: Mapped[List['PasswordResetToken']] = relationship(cascade='all, delete-orphan', back_populates='user')
    audit_logs: Mapped[List['AuditLog']] = relationship(back_populates='user')


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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True)

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
    __table_args__ = (
        UniqueConstraint('subject_type', 'subject_id', 'ip_address', name='uq_rating_subject_ip'),
    )

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
    'RATE_SHOWCASE': 'Valoración de vitrina',
    'UNAUTHORIZED_ACCESS': 'Acceso no autorizado',
    'CSRF_FAILURE': 'Fallo de validación CSRF',
    'TOKEN_VALIDATION_FAILED': 'Fallo de validación de token',
}


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Habilita claves foráneas en SQLite para asegurar la integridad referencial (Seguridad)."""
    if DATABASE_URL.startswith('sqlite'):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


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


def _get_s3_client():
    """Obtiene el cliente S3/R2 compartido (Optimización Bolt: singleton)."""
    global _S3_CLIENT
    if _S3_CLIENT is not None:
        return _S3_CLIENT

    try:
        import boto3
        from botocore.config import Config

        r2_account_id = os.environ.get('R2_ACCOUNT_ID')
        r2_access_key_id = os.environ.get('R2_ACCESS_KEY_ID')
        r2_secret_access_key = os.environ.get('R2_SECRET_ACCESS_KEY')
        r2_endpoint_url = os.environ.get('R2_ENDPOINT_URL')

        if not r2_endpoint_url and r2_account_id:
            r2_endpoint_url = f"https://{r2_account_id}.r2.cloudflarestorage.com"

        _S3_CLIENT = boto3.client(
            's3',
            endpoint_url=r2_endpoint_url,
            aws_access_key_id=r2_access_key_id,
            aws_secret_access_key=r2_secret_access_key,
            config=Config(signature_version='s3v4'),
            region_name='auto'
        )
        return _S3_CLIENT
    except Exception as exc:
        # Avoid circular dependencies or runtime errors if accessed outside Flask context.
        try:
            current_app.logger.error('s3_client_initialization_failed error=%s', exc)
        except RuntimeError:
            pass
        return None


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
                    text(f"UPDATE users SET homepage_showcase_opt_in = {default_false} WHERE homepage_showcase_opt_in IS NULL")
                )

        # Asegurar índices para filtros y ordenamientos comunes (Fuera del bloque condicional para mayor robustez)
        with engine.begin() as connection:
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_collection_visibility ON users (collection_visibility)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_homepage_showcase_opt_in ON users (homepage_showcase_opt_in)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_created_at ON users (created_at)'))
            connection.execute(text('CREATE INDEX IF NOT EXISTS ix_users_updated_at ON users (updated_at)'))

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

    if alter_statements:
        with engine.begin() as connection:
            for statement in alter_statements:
                connection.execute(text(statement))
            connection.execute(text("UPDATE games SET categoria = 'Biblioteca' WHERE categoria IS NULL OR categoria = ''"))
            connection.execute(text("UPDATE games SET prioridad = 'Media' WHERE prioridad IS NULL OR prioridad = ''"))
            connection.execute(text(f"UPDATE games SET es_favorito = {default_false} WHERE es_favorito IS NULL"))

    # Asegurar índices para filtros y ordenamientos comunes (Fuera del bloque condicional para mayor robustez)
    with engine.begin() as connection:
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_games_created_at ON games (created_at)'))
        connection.execute(text('CREATE INDEX IF NOT EXISTS ix_games_updated_at ON games (updated_at)'))
        # Asegurar integridad de valoraciones (Unique Constraint)
        connection.execute(text('CREATE UNIQUE INDEX IF NOT EXISTS uq_rating_subject_ip ON showcase_ratings (subject_type, subject_id, ip_address)'))


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


def as_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def user_to_dict(user: User | None, format_dates: bool = True) -> Optional[Dict[str, Any]]:
    """Convierte un usuario en diccionario. Optimización Bolt: Deferir formateo de fechas."""
    if user is None:
        return None
    return _user_row_to_dict(user, format_dates=format_dates)


def _user_row_to_dict(row: Any, format_dates: bool = True) -> Dict[str, Any]:
    """Mapea una fila de DB o instancia de User a un diccionario (Optimización Bolt)."""
    # Bolt Optimization: Support mapping for specific field selections.
    if isinstance(row, dict):
        if format_dates:
            for field in ('created_at', 'updated_at'):
                if field in row:
                    row[field] = as_iso(row[field])
        return row

    # Centralized normalization to UTC-aware datetimes for consistency.
    _MIN_DATE = MIN_DATE
    cre = getattr(row, 'created_at', _MIN_DATE) or _MIN_DATE
    if cre.tzinfo is None: cre = cre.replace(tzinfo=timezone.utc)
    upd = getattr(row, 'updated_at', _MIN_DATE) or _MIN_DATE
    if upd.tzinfo is None: upd = upd.replace(tzinfo=timezone.utc)

    if format_dates:
        cre, upd = cre.isoformat(), upd.isoformat()

    return {
        'user_id': row.user_id,
        'email': row.email,
        'nombre': row.nombre,
        'apellido': row.apellido,
        'prefijo_pais': row.prefijo_pais,
        'telefono': row.telefono,
        'password_hash': row.password_hash,
        'role': row.role,
        'status': row.status,
        'collection_visibility': row.collection_visibility,
        'homepage_showcase_opt_in': row.homepage_showcase_opt_in,
        'created_at': cre,
        'updated_at': upd,
    }


def game_to_dict(game: Game | None, format_dates: bool = True) -> Optional[Dict[str, Any]]:
    """Convierte un juego en diccionario. Optimización Bolt: Deferir formateo de fechas."""
    if game is None:
        return None
    return _game_row_to_dict(game, format_dates=format_dates)


def _game_row_to_dict(row: Any, format_dates: bool = True) -> Dict[str, Any]:
    """Mapea una fila de DB o instancia de Game a un diccionario (Optimización Bolt)."""
    # Centralized normalization to UTC-aware datetimes for consistency.
    _MIN_DATE = MIN_DATE
    cre = row.created_at or _MIN_DATE
    if cre.tzinfo is None: cre = cre.replace(tzinfo=timezone.utc)
    upd = row.updated_at or _MIN_DATE
    if upd.tzinfo is None: upd = upd.replace(tzinfo=timezone.utc)

    if format_dates:
        cre, upd = cre.isoformat(), upd.isoformat()

    return {
        'game_id': row.game_id,
        'user_id': row.user_id,
        # Bolt Optimization: Normalize strings to empty strings for null-safe .lower() in routes.
        'titulo': row.titulo or '',
        'descripcion': row.descripcion or '',
        'imagen_url': row.imagen_url,
        # Bolt Optimization: Normalize categorical fields to model defaults if null.
        'plataforma': row.plataforma or 'PC',
        'estado': row.estado or 'N/A',
        'categoria': row.categoria or 'Biblioteca',
        'prioridad': row.prioridad or 'Media',
        'calificacion': row.calificacion,
        'es_favorito': row.es_favorito,
        'created_at': cre,
        'updated_at': upd,
    }


def obtener_metricas_coleccion(user_id: str, full: bool = True) -> Dict[str, Any]:
    """Calcula métricas de la colección directamente en la base de datos (Bolt optimization)."""
    ensure_tables()
    session_factory = get_session_factory()
    now = utcnow()
    recent_cutoff = now - timedelta(days=7)
    stale_cutoff = now - timedelta(days=30)

    with session_factory() as session:
        # 1. Agregaciones básicas en un solo round-trip
        metrics = session.execute(
            select(
                func.count(Game.game_id).label('total_games'),
                func.sum(case((Game.imagen_url.is_(None), 1), else_=0)).label('missing_images'),
                func.sum(case((Game.es_favorito.is_(True), 1), else_=0)).label('favorites_count'),
                func.sum(case((Game.prioridad == 'Alta', 1), else_=0)).label('high_priority_count'),
                func.sum(case((Game.created_at >= recent_cutoff, 1), else_=0)).label('recently_added'),
                func.sum(case((Game.updated_at >= recent_cutoff, 1), else_=0)).label('recently_updated'),
                func.sum(case((Game.updated_at < stale_cutoff, 1), else_=0)).label('stale_games'),
                func.sum(case((Game.categoria == 'Wishlist', 1), else_=0)).label('wishlist_count'),
                func.sum(case((Game.categoria == 'Backlog', 1), else_=0)).label('backlog_count'),
                func.sum(case((Game.categoria == 'Jugando', 1), else_=0)).label('currently_playing_count'),
                func.avg(Game.calificacion).label('average_rating'),
                func.count(func.distinct(func.coalesce(Game.plataforma, 'Sin plataforma'))).label('platforms_count')
            ).where(Game.user_id == user_id)
        ).first()

        # Initialize base results with scalar metrics from the first query.
        results = {
            'total_games': metrics.total_games if metrics else 0,
            'platforms_count': metrics.platforms_count if metrics else 0,
            'recently_added': int(metrics.recently_added or 0) if metrics else 0,
            'recently_updated': int(metrics.recently_updated or 0) if metrics else 0,
            'recent_activity': 0,
            'missing_images': int(metrics.missing_images or 0) if metrics else 0,
            'favorites_count': int(metrics.favorites_count or 0) if metrics else 0,
            'high_priority_count': int(metrics.high_priority_count or 0) if metrics else 0,
            'stale_games': int(metrics.stale_games or 0) if metrics else 0,
            'wishlist_count': int(metrics.wishlist_count or 0) if metrics else 0,
            'backlog_count': int(metrics.backlog_count or 0) if metrics else 0,
            'currently_playing_count': int(metrics.currently_playing_count or 0) if metrics else 0,
            'average_rating': round(float(metrics.average_rating), 1) if metrics and metrics.average_rating is not None else None,
            'dominant_platform': {'label': 'Sin juegos', 'count': 0},
            'dominant_status': {'label': 'N/A', 'count': 0},
            'dominant_category': {'label': 'Biblioteca', 'count': 0},
            'last_updated_game': None,
            'next_focus': None,
            'filter_options': {'plataformas': [], 'estados': [], 'categorias': []}
        }

        if not full:
            return results

        # Bolt optimization: Calculate recent activity from logs in a separate scalar query
        # to avoid complex joins that could impact performance on large datasets.
        results['recent_activity'] = session.scalar(
            select(func.count(AuditLog.audit_id))
            .where(AuditLog.user_id == user_id, AuditLog.timestamp >= recent_cutoff)
        ) or 0

        if not metrics or metrics.total_games == 0:
            return results

        # 2. Dominantes (Platform, Status, Category)
        def get_dominant(column):
            return session.execute(
                select(column, func.count(Game.game_id))
                .where(Game.user_id == user_id)
                .group_by(column)
                .order_by(func.count(Game.game_id).desc())
                .limit(1)
            ).first()

        dom_platform = get_dominant(Game.plataforma)
        dom_status = get_dominant(Game.estado)
        dom_category = get_dominant(Game.categoria)

        results.update({
            'dominant_platform': {'label': dom_platform[0] if dom_platform else 'Sin plataforma', 'count': dom_platform[1] if dom_platform else 0},
            'dominant_status': {'label': dom_status[0] if dom_status else 'N/A', 'count': dom_status[1] if dom_status else 0},
            'dominant_category': {'label': dom_category[0] if dom_category else 'Biblioteca', 'count': dom_category[1] if dom_category else 0},
        })

        # 3. Last updated y Next focus
        last_updated = session.scalar(
            select(Game).where(Game.user_id == user_id).order_by(Game.updated_at.desc(), Game.created_at.desc()).limit(1)
        )
        next_focus = session.scalar(
            select(Game)
            .where(Game.user_id == user_id, Game.prioridad == 'Alta', Game.categoria != 'Completado')
            .order_by(Game.updated_at.asc())
            .limit(1)
        )

        results.update({
            'last_updated_game': game_to_dict(last_updated),
            'next_focus': game_to_dict(next_focus),
        })

        # 4. Filter Options (Excluyendo valores por defecto para coincidir con la lógica previa)
        results['filter_options'] = {
            'plataformas': list(session.scalars(select(func.distinct(Game.plataforma)).where(Game.user_id == user_id, Game.plataforma.isnot(None), Game.plataforma != 'Sin plataforma').order_by(Game.plataforma)).all()),
            'estados': list(session.scalars(select(func.distinct(Game.estado)).where(Game.user_id == user_id, Game.estado.isnot(None), Game.estado != 'N/A').order_by(Game.estado)).all()),
            'categorias': list(session.scalars(select(func.distinct(Game.categoria)).where(Game.user_id == user_id).order_by(Game.categoria)).all()),
        }

        return results


def reset_token_to_dict(item: PasswordResetToken | None) -> Optional[Dict[str, Any]]:
    if item is None:
        return None
    return {
        'token_id': item.token_id,
        'user_id': item.user_id,
        'reset_token': item.reset_token,
        'created_at': as_iso(item.created_at),
        'expires_at': as_iso(item.expires_at),
        'expires_at_unix': int(item.expires_at.timestamp()),
        'used': item.used,
        'used_at': as_iso(item.used_at),
        'ip_address': item.ip_address,
    }


def audit_log_to_dict(item: AuditLog | None, format_dates: bool = True) -> Optional[Dict[str, Any]]:
    """Convierte un log en diccionario. Optimización Bolt: Deferir formateo de fechas."""
    if item is None:
        return None
    return _audit_log_row_to_dict(item, format_dates=format_dates)


def _audit_log_row_to_dict(row: Any, format_dates: bool = True) -> Dict[str, Any]:
    """Mapea una fila de DB o instancia de AuditLog a un diccionario (Optimización Bolt)."""
    ts = row.timestamp or MIN_DATE
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)

    if format_dates:
        ts = ts.isoformat()

    return {
        'audit_id': row.audit_id,
        'user_id': row.user_id,
        'action': row.action,
        'action_name': row.action_name,
        'resource': row.resource,
        'timestamp': ts,
        'ip_address': row.ip_address,
        'user_agent': row.user_agent,
        'details': row.details or {},
        'status': row.status,
    }


def parse_date_filter(value: str, *, end: bool = False) -> Optional[datetime]:
    """Convierte filtros de fecha simple a datetime UTC."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if end:
        parsed = parsed + timedelta(days=1)
    return parsed


def validar_email(email):
    """Valida el formato y longitud del email (max 255)."""
    if not email or len(email) > 255:
        return False
    # Bolt Optimization: Use pre-compiled regex.
    return _EMAIL_RE.match(email) is not None


def validar_telefono(telefono):
    """Valida que el teléfono contenga solo dígitos y tenga longitud válida (7-20)."""
    return telefono.isdigit() and 7 <= len(telefono) <= 20


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


def subir_imagen_a_s3(archivo):
    """Sube una portada usando el backend de storage disponible."""
    try:
        storage_backend = current_app.config.get('STORAGE_BACKEND', STORAGE_BACKEND)
    except RuntimeError:
        storage_backend = STORAGE_BACKEND

    if storage_backend == 'none':
        try:
            current_app.logger.info('image_upload_skipped storage_backend=none')
        except RuntimeError:
            pass
        return None

    valid, error = is_valid_image_file(archivo)
    if not valid:
        try:
            current_app.logger.warning('image_validation_failed reason=%s', error)
        except RuntimeError:
            pass
        return None

    try:
        extension = os.path.splitext(secure_filename(archivo.filename))[1].lower()
        nombre_unico = f"covers/{uuid.uuid4()}{extension}"

        if storage_backend == 'local':
            local_upload_dir = current_app.config.get('LOCAL_UPLOAD_DIR', LOCAL_UPLOAD_DIR)
            local_upload_url_path = current_app.config.get('LOCAL_UPLOAD_URL_PATH', LOCAL_UPLOAD_URL_PATH)
            upload_dir = os.path.join(local_upload_dir, 'covers')
            os.makedirs(upload_dir, exist_ok=True)
            destination = os.path.join(upload_dir, os.path.basename(nombre_unico))
            archivo.save(destination)
            return f"{local_upload_url_path}/{nombre_unico}"

        # Soporte para R2 / S3
        s3_client = _get_s3_client()
        r2_bucket_name = os.environ.get('R2_BUCKET_NAME')
        r2_endpoint_url = os.environ.get('R2_ENDPOINT_URL')
        r2_account_id = os.environ.get('R2_ACCOUNT_ID')

        if not r2_endpoint_url and r2_account_id:
            r2_endpoint_url = f"https://{r2_account_id}.r2.cloudflarestorage.com"

        s3_client.upload_fileobj(
            archivo,
            r2_bucket_name,
            nombre_unico,
            ExtraArgs={'ContentType': archivo.content_type}
        )

        if r2_endpoint_url:
            return f"{r2_endpoint_url}/{r2_bucket_name}/{nombre_unico}"
        return f"https://{r2_bucket_name}.s3.amazonaws.com/{nombre_unico}"
    except Exception as exc:
        try:
            current_app.logger.error('image_upload_unexpected_error error=%s', exc)
        except RuntimeError:
            pass
        return None


def validar_password(password):
    """Valida que la contraseña tenga una longitud segura (8-128) y complejidad básica."""
    # El límite superior de 128 protege contra ataques DoS al algoritmo de hashing.
    if not (8 <= len(password) <= 128):
        return False

    # Bloquear contraseñas extremadamente comunes que pasan la validación de complejidad (Seguridad mejorada)
    if password.lower() in _COMMON_WEAK_PASSWORDS:
        return False

    # Requerir al menos una letra y un número (Seguridad mejorada)
    return any(c.isalpha() for c in password) and any(c.isdigit() for c in password)


def eliminar_imagen_s3(imagen_url):
    """Elimina una imagen del backend de almacenamiento (Local o R2/S3)."""
    if not imagen_url:
        return True

    try:
        storage_backend = current_app.config.get('STORAGE_BACKEND', STORAGE_BACKEND)
        local_upload_url_path = current_app.config.get('LOCAL_UPLOAD_URL_PATH', LOCAL_UPLOAD_URL_PATH)
        local_upload_dir = current_app.config.get('LOCAL_UPLOAD_DIR', LOCAL_UPLOAD_DIR)
    except RuntimeError:
        storage_backend = STORAGE_BACKEND
        local_upload_url_path = LOCAL_UPLOAD_URL_PATH
        local_upload_dir = LOCAL_UPLOAD_DIR

    if storage_backend == 'local' and imagen_url.startswith(local_upload_url_path + '/'):
        relative_path = imagen_url.replace(local_upload_url_path + '/', '', 1).lstrip('/')
        destination = os.path.abspath(os.path.join(local_upload_dir, relative_path))
        upload_root = os.path.abspath(local_upload_dir)
        if destination.startswith(upload_root) and os.path.exists(destination):
            try:
                os.remove(destination)
            except OSError:
                return False
        return True

    if storage_backend in {'r2', 's3'}:
        try:
            r2_bucket_name = os.environ.get('R2_BUCKET_NAME')
            if not r2_bucket_name:
                return False

            s3_client = _get_s3_client()
            if not s3_client:
                return False

            key = obtener_key_desde_url(imagen_url)
            if not key:
                return False

            s3_client.delete_object(Bucket=r2_bucket_name, Key=key)
            return True
        except Exception:
            return False

    return True


def obtener_key_desde_url(imagen_url):
    """Extrae el Object Key de una URL de S3 o R2 con validación de prefijo."""
    if not imagen_url:
        return None
    try:
        parsed = urlparse(imagen_url)
        # Normalize to prevent bypasses via backslashes, encoding, or multiple slashes (Security hardening)
        path = unquote(parsed.path).replace('\\', '/').lstrip('/')
        # os.path.normpath collapses redundancies like '..' and '.' (Security hardening)
        normalized_path = os.path.normpath(path).replace('\\', '/')

        # Si la URL es tipo http://endpoint/bucket/key
        r2_bucket_name = os.environ.get('R2_BUCKET_NAME')
        if r2_bucket_name and normalized_path.startswith(r2_bucket_name + '/'):
            normalized_path = normalized_path.replace(r2_bucket_name + '/', '', 1)

        # Defensa en profundidad: solo permitir llaves dentro del prefijo de portadas
        if normalized_path.startswith('covers/'):
            return normalized_path
        return None
    except Exception:
        return None


def crear_url_firmada_lectura(imagen_url: str, expires_in: int = 3600) -> str:
    """Genera una URL firmada para lectura si el backend es R2/S3, o devuelve la URL original."""
    if not imagen_url or not imagen_url.startswith('http'):
        return imagen_url or ''

    try:
        storage_backend = current_app.config.get('STORAGE_BACKEND', STORAGE_BACKEND)
    except RuntimeError:
        storage_backend = STORAGE_BACKEND
    if storage_backend not in {'r2', 's3'}:
        return imagen_url

    try:
        r2_bucket_name = os.environ.get('R2_BUCKET_NAME')
        if not r2_bucket_name:
            return imagen_url

        s3_client = _get_s3_client()
        if not s3_client:
            return imagen_url

        key = obtener_key_desde_url(imagen_url)
        if not key:
            return imagen_url

        signed_url = s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': r2_bucket_name, 'Key': key},
            ExpiresIn=expires_in
        )
        return signed_url
    except Exception:
        return imagen_url


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
    """Obtiene todos los juegos de un usuario (Optimización Bolt: bypass ORM hydration)."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        # Fetching specific columns directly instead of full ORM objects to bypass hydration overhead.
        results = session.execute(
            select(
                Game.game_id, Game.user_id, Game.titulo, Game.descripcion,
                Game.imagen_url, Game.plataforma, Game.estado, Game.categoria,
                Game.prioridad, Game.calificacion, Game.es_favorito,
                Game.created_at, Game.updated_at
            )
            .where(Game.user_id == user_id)
            .order_by(Game.updated_at.desc(), Game.created_at.desc())
        ).all()

        # Bolt Optimization: Reuse _game_row_to_dict for consistent normalization and performance.
        return [_game_row_to_dict(row, format_dates=False) for row in results]


def obtener_juego_por_id(user_id, game_id, format_dates: bool = True):
    """Obtiene un juego por ID y usuario (Optimización Bolt: bypass ORM hydration)."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.execute(
            select(Game.__table__).where(Game.user_id == user_id, Game.game_id == game_id)
        ).first()
        return _game_row_to_dict(row, format_dates=format_dates) if row else None


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


def obtener_usuario_por_email(email, format_dates: bool = True):
    """Obtiene un usuario por email (Optimización Bolt: bypass ORM hydration)."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.execute(
            select(User.__table__).where(User.email == email.lower().strip())
        ).first()
        return _user_row_to_dict(row, format_dates=format_dates) if row else None


def verificar_credenciales(email, password, format_dates: bool = True):
    """Compatibilidad con la interfaz previa."""
    return obtener_usuario_por_email(email, format_dates=format_dates)


def obtener_todos_usuarios(limit: int | None = None, offset: int | None = None, **kwargs) -> List[Dict[str, Any]]:
    """Obtiene todos los usuarios (Optimización Bolt: bypass ORM hydration)."""
    format_dates = kwargs.get('format_dates', True)
    ensure_tables()
    session_factory = get_session_factory()

    # Fetching the full table via select(User.__table__) bypasses ORM hydration
    # but ensures we get all columns even if the schema changes.
    query = select(User.__table__).order_by(User.created_at.desc())

    if limit is not None:
        query = query.limit(limit)
    if offset is not None:
        query = query.offset(offset)

    with session_factory() as session:
        results = session.execute(query).all()
        return [_user_row_to_dict(row, format_dates=format_dates) for row in results]


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
        # Truncate IP to match DB schema (Security hardening)
        ip_address=(ip_address or 'unknown')[:64],
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


def redact_sensitive_details(data: Any, depth: int = 0) -> Any:
    """Máscara valores sensibles y trunca strings largos en logs (Seguridad)."""
    if depth > 10:
        return '[MAX_DEPTH_REACHED]'

    if data is None:
        return None

    if isinstance(data, dict):
        redacted_dict = {}
        # Breadth limit to prevent Log-DoS (Security hardening)
        for i, (k, v) in enumerate(data.items()):
            if i >= 100:
                redacted_dict['[BREADTH_LIMIT_REACHED]'] = '...'
                break
            key_lower = str(k).lower()
            if any(pattern in key_lower for pattern in _SENSITIVE_PATTERNS):
                redacted_dict[k] = '[REDACTED]'
            else:
                redacted_dict[k] = redact_sensitive_details(v, depth + 1)
        return redacted_dict

    if isinstance(data, (list, tuple, set)):
        redacted_list = []
        # Breadth limit to prevent Log-DoS (Security hardening)
        for i, item in enumerate(data):
            if i >= 100:
                redacted_list.append('[BREADTH_LIMIT_REACHED]')
                break
            redacted_list.append(redact_sensitive_details(item, depth + 1))
        return redacted_list

    if isinstance(data, (str, bytes)):
        # Handle bytes safely and truncate strings to prevent storage-based DoS
        val = data.decode('utf-8', errors='replace') if isinstance(data, bytes) else data
        return val[:1024]

    if isinstance(data, (int, float, bool)):
        return data

    # Safe fallback for non-serializable types to prevent DB errors (Security resilience)
    return str(data)[:1024]


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

    # Harden and truncate strings to match DB schema constraints
    safe_action = (action or 'UNKNOWN')[:80]
    safe_resource = (resource or 'UNKNOWN')[:80]
    derived_name = AUDIT_ACTIONS.get(action, safe_action)[:120]

    # Bolt Optimization: Redact sensitive details once to avoid redundant recursive calls in the retry block.
    # Traceability enhancement: Automatically inject request_id if within a request context.
    safe_details = details.copy() if isinstance(details, dict) else {}
    try:
        from flask import g
        if hasattr(g, 'request_id') and 'request_id' not in safe_details:
            safe_details['request_id'] = g.request_id
    except (ImportError, RuntimeError):
        pass

    safe_details = redact_sensitive_details(safe_details)

    item = AuditLog(
        audit_id=str(uuid.uuid4()),
        user_id=user_id,
        action=safe_action,
        action_name=derived_name,
        resource=safe_resource,
        timestamp=utcnow(),
        # Ensure fields fit database constraints (Security hardening)
        ip_address=(ip_address or 'unknown')[:64],
        user_agent=(user_agent or 'unknown')[:500],
        details=safe_details,
        status=status[:20],
    )
    with session_factory() as session:
        session.add(item)
        try:
            session.commit()
        except IntegrityError:
            # Fallback for deleted users (Security resilience)
            session.rollback()
            # item is expired after rollback, we must create a new one to retry safely
            # Bolt Optimization: Reuse already redacted details.
            safe_details['attempted_user_id'] = user_id
            item = AuditLog(
                audit_id=str(uuid.uuid4()),
                user_id=None,
                action=safe_action,
                action_name=derived_name,
                resource=safe_resource,
                timestamp=utcnow(),
                ip_address=(ip_address or 'unknown')[:64],
                user_agent=(user_agent or 'unknown')[:500],
                details=safe_details,
                status=status[:20],
            )
            session.add(item)
            session.commit()
        return {'success': True, 'audit_id': item.audit_id, 'error': None}


def obtener_logs_por_usuario(user_id: str, limit: int = 50, **kwargs) -> List[Dict[str, Any]]:
    """Obtiene logs recientes de un usuario (Optimización Bolt: bypass ORM hydration)."""
    format_dates = kwargs.get('format_dates', True)
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        # Use select(AuditLog.__table__) to bypass ORM hydration
        results = session.execute(
            select(AuditLog.__table__)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.timestamp.desc())
            .limit(limit)
        ).all()
        return [_audit_log_row_to_dict(row, format_dates=format_dates) for row in results]


def obtener_todos_logs(filters: Dict[str, Any] = None, limit: int = 100, **kwargs) -> List[Dict[str, Any]]:
    """Obtiene logs de auditoría con filtros opcionales (Optimización Bolt: bypass ORM hydration)."""
    format_dates = kwargs.get('format_dates', True)
    ensure_tables()
    session_factory = get_session_factory()
    filters = filters or {}

    # Use select(AuditLog.__table__) to bypass ORM hydration
    query = select(AuditLog.__table__)
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
        results = session.execute(query).all()
        return [_audit_log_row_to_dict(row, format_dates=format_dates) for row in results]


def obtener_estadisticas_logs() -> Dict[str, Any]:
    """Calcula estadísticas simples de auditoría usando agregaciones en base de datos.
    Optimización Bolt: Se eliminaron las consultas de action_counts y daily_activity
    ya que no se utilizan en las plantillas actuales, ahorrando 2 roundtrips a la DB."""
    ensure_tables()
    session_factory = get_session_factory()

    with session_factory() as session:
        # 1. Status counts (Consolidated: we calculate total_logs from these counts to save one DB roundtrip)
        status_results = session.execute(
            select(AuditLog.status, func.count(AuditLog.audit_id)).group_by(AuditLog.status)
        ).all()
        status_counts = {row[0]: row[1] for row in status_results}
        total_logs = sum(status_counts.values())

        if total_logs == 0:
            return {
                'total_logs': 0,
                'status_counts': {},
                'top_users': [],
                'success_rate': 100.0,
            }

        # 2. Top users
        user_results = session.execute(
            select(AuditLog.user_id, func.count(AuditLog.audit_id))
            .group_by(AuditLog.user_id)
            .order_by(func.count(AuditLog.audit_id).desc())
            .limit(5)
        ).all()
        top_users = [(row[0] or 'anonymous', row[1]) for row in user_results]

        success_count = status_counts.get('SUCCESS', 0)
        success_rate = round((success_count / total_logs * 100), 2)

        return {
            'total_logs': total_logs,
            'status_counts': status_counts,
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

    for log in logs:
        row = {}
        for key in fieldnames[:-1]:
            val = str(log.get(key, '') or '')
            # Strip leading whitespace before checking for risky characters to prevent formula bypasses (CSV Injection)
            # Bolt Optimization: Use module-level constant.
            if val.lstrip().startswith(_RISKY_CSV_CHARS):
                val = "'" + val
            row[key] = val

        details_val = str(log.get('details', {}) or '{}')
        if details_val.lstrip().startswith(_RISKY_CSV_CHARS):
            details_val = "'" + details_val
        row['details'] = details_val

        writer.writerow(row)
    return output.getvalue()


def obtener_usuario_por_id(user_id: str, format_dates: bool = True) -> Optional[Dict[str, Any]]:
    """Obtiene un usuario por ID (Optimización Bolt: bypass ORM hydration)."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        row = session.execute(
            select(User.__table__).where(User.user_id == user_id)
        ).first()
        return _user_row_to_dict(row, format_dates=format_dates) if row else None


def obtener_usuarios_por_ids(user_ids: List[str], **kwargs) -> List[Dict[str, Any]]:
    """Obtiene múltiples usuarios por IDs (Optimización Bolt: bypass ORM hydration)."""
    if not user_ids:
        return []
    format_dates = kwargs.get('format_dates', True)
    # Bolt optimization: Allow fetching specific columns to reduce DB load.
    fields = kwargs.get('fields')
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        if fields:
            # SQL: SELECT user_id, email, nombre ... FROM users
            query = select(*[getattr(User, f) for f in fields])
        else:
            # Fetching the full table via select(User.__table__) bypasses ORM hydration
            # while keeping the data layer robust against schema changes.
            query = select(User.__table__)

        results = session.execute(query.where(User.user_id.in_(user_ids))).all()

        if fields:
            # Manual mapping for specific field selections using the normalized helper.
            return [_user_row_to_dict(dict(zip(fields, row)), format_dates=format_dates) for row in results]
        return [_user_row_to_dict(row, format_dates=format_dates) for row in results]


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
    offset: int | None = None,
    homepage_only: bool = False,
) -> List[Dict[str, Any]]:
    """Obtiene resúmenes de colecciones de usuarios (Optimización Bolt: Scalar subqueries)."""
    ensure_tables()
    session_factory = get_session_factory()

    with session_factory() as session:
        # Bolt Optimization: Correlated subqueries for games metrics.
        # This avoids massive joins and group-bys on the main query, which is
        # significantly more efficient for paginated admin and showcase views.
        total_games_sub = (
            select(func.count(Game.game_id))
            .where(Game.user_id == User.user_id)
            .correlate(User)
            .scalar_subquery()
        )
        favorites_count_sub = (
            select(func.coalesce(func.sum(case((Game.es_favorito.is_(True), 1), else_=0)), 0))
            .where(Game.user_id == User.user_id)
            .correlate(User)
            .scalar_subquery()
        )
        average_rating_sub = (
            select(func.avg(Game.calificacion))
            .where(Game.user_id == User.user_id)
            .correlate(User)
            .scalar_subquery()
        )
        last_updated_sub = (
            select(func.max(func.coalesce(Game.updated_at, Game.created_at)))
            .where(Game.user_id == User.user_id)
            .correlate(User)
            .scalar_subquery()
        )
        dominant_platform_sub = (
            select(Game.plataforma)
            .where(Game.user_id == User.user_id)
            .group_by(Game.plataforma)
            .order_by(func.count(Game.game_id).desc())
            .limit(1)
            .correlate(User)
            .scalar_subquery()
        )

        # Bolt Optimization: Eagerly fetch showcase ratings in the same round-trip.
        showcase_avg_sub = (
            select(func.avg(ShowcaseRating.rating))
            .where(ShowcaseRating.subject_id == User.user_id, ShowcaseRating.subject_type == 'public')
            .correlate(User)
            .scalar_subquery()
        )
        showcase_votes_sub = (
            select(func.count(ShowcaseRating.rating))
            .where(ShowcaseRating.subject_id == User.user_id, ShowcaseRating.subject_type == 'public')
            .correlate(User)
            .scalar_subquery()
        )

        query = select(
            User.user_id,
            User.nombre,
            User.email,
            User.collection_visibility,
            User.homepage_showcase_opt_in,
            func.coalesce(total_games_sub, 0).label('total_games'),
            func.coalesce(favorites_count_sub, 0).label('favorites_count'),
            average_rating_sub.label('average_rating'),
            last_updated_sub.label('last_updated_at'),
            func.coalesce(dominant_platform_sub, 'Sin juegos').label('dominant_platform'),
            showcase_avg_sub.label('showcase_rating_average'),
            func.coalesce(showcase_votes_sub, 0).label('showcase_votes_count'),
        )

        if homepage_only:
            # Bolt Optimization: Use exists() for efficient filtering of users with content.
            has_games = select(1).where(Game.user_id == User.user_id).limit(1).exists()
            query = query.where(User.homepage_showcase_opt_in.is_(True), has_games)

        if visibility:
            query = query.where(User.collection_visibility == visibility)

        # Ordenamiento en SQL: Rating desc, Favoritos desc, Total desc, Actualización desc.
        query = query.order_by(
            func.coalesce(average_rating_sub, -1).desc(),
            favorites_count_sub.desc(),
            total_games_sub.desc(),
            last_updated_sub.desc(),
        )

        if limit:
            query = query.limit(limit)
        if offset:
            query = query.offset(offset)

        results = session.execute(query).all()
        if not results:
            return []

        return [
            {
                'user_id': r.user_id,
                'owner_name': r.nombre or 'Coleccionista',
                'owner_email': r.email,
                'collection_visibility': r.collection_visibility,
                'homepage_showcase_opt_in': bool(r.homepage_showcase_opt_in),
                'total_games': int(r.total_games),
                'favorites_count': int(r.favorites_count),
                'average_rating': round(float(r.average_rating), 1) if r.average_rating is not None else None,
                'dominant_platform': r.dominant_platform,
                'last_updated_at': as_iso(r.last_updated_at) or '',
                'showcase_rating_average': round(float(r.showcase_rating_average), 1) if r.showcase_rating_average is not None else None,
                'showcase_votes_count': int(r.showcase_votes_count),
            }
            for r in results
        ]


def contar_resumenes_colecciones(
    visibility: str | None = None,
    homepage_only: bool = False,
) -> int:
    """Cuenta el total de colecciones que coinciden con los filtros (optimizado)."""
    ensure_tables()
    session_factory = get_session_factory()

    with session_factory() as session:
        query = select(func.count(User.user_id))

        if homepage_only:
            # Para el home, solo contamos si tienen juegos (usando subquery correlacionada eficiente)
            has_games = select(1).where(Game.user_id == User.user_id).limit(1).exists()
            query = query.where(
                User.homepage_showcase_opt_in.is_(True),
                has_games,
            )

        if visibility:
            query = query.where(User.collection_visibility == visibility)

        return session.scalar(query) or 0


def obtener_colecciones_publicas(limit: int = 6) -> List[Dict[str, Any]]:
    """Devuelve colecciones públicas con algo real que mostrar (ahora optimizado)."""
    return obtener_resumenes_colecciones(visibility='public', limit=limit, homepage_only=True)


def verificar_coleccion_publica(user_id: str) -> bool:
    """Verifica de forma eficiente si una colección es elegible para showcase.
    Optimización Bolt: Evita cargar múltiples registros para una validación de existencia."""
    ensure_tables()
    session_factory = get_session_factory()
    with session_factory() as session:
        # Usamos exists() correlacionado para verificar contenido sin cargar filas.
        has_games = select(1).where(Game.user_id == User.user_id).limit(1).exists()
        stmt = select(User.user_id).where(
            User.user_id == user_id,
            User.collection_visibility == 'public',
            User.homepage_showcase_opt_in.is_(True),
            has_games,
        )
        return session.execute(stmt).first() is not None


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
    """Enriquece colecciones con valoración pública en batch para evitar N+1 queries (Optimizado: in-place)."""
    if not items:
        return []

    subject_ids = [str(item[subject_id_key]) for item in items]
    ratings_map = obtener_ratings_multiple(subject_type, subject_ids)

    for item in items:
        subject_id = str(item[subject_id_key])
        actual_rating = ratings_map.get(subject_id, {'average': None, 'votes_count': 0})

        rating_summary = combinar_rating_showcase(
            actual_rating,
            base_average=item.get(default_rating_key) if default_rating_key else None,
            base_votes_count=item.get(default_votes_key, 0) if default_votes_key else 0,
        )
        item['showcase_rating_average'] = rating_summary['average']
        item['showcase_votes_count'] = rating_summary['votes_count']
    return items


def registrar_rating_showcase(subject_type: str, subject_id: str, rating: int, ip_address: str) -> Dict[str, Any]:
    """Guarda una valoración pública, una por IP y colección."""
    ensure_tables()
    if rating not in {1, 2, 3, 4, 5}:
        return {'success': False, 'duplicate': False, 'error': 'La valoración debe estar entre 1 y 5.'}

    session_factory = get_session_factory()
    safe_ip = (ip_address or 'unknown')[:64]
    with session_factory() as session:
        # Bolt Optimization: Maintain duplicate check as requested by review to preserve explicit logic,
        # while keeping the IntegrityError fallback for race conditions.
        existing = session.scalar(
            select(ShowcaseRating).where(
                ShowcaseRating.subject_type == subject_type,
                ShowcaseRating.subject_id == subject_id,
                ShowcaseRating.ip_address == safe_ip,
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

        try:
            entry = ShowcaseRating(
                rating_id=str(uuid.uuid4()),
                subject_type=subject_type,
                subject_id=subject_id,
                ip_address=safe_ip,
                rating=rating,
                created_at=utcnow(),
            )
            session.add(entry)
            session.commit()
        except IntegrityError:
            session.rollback()
            summary = obtener_rating_showcase(subject_type, subject_id)
            return {
                'success': False,
                'duplicate': True,
                'error': 'Esta IP ya valoró esta colección.',
                'average': summary['average'],
                'votes_count': summary['votes_count'],
            }

    summary = obtener_rating_showcase(subject_type, subject_id)
    return {
        'success': True,
        'duplicate': False,
        'error': None,
        'average': summary['average'],
        'votes_count': summary['votes_count'],
    }


def crear_presigned_upload(nombre_archivo: str, content_type: str, max_upload_bytes: int) -> Dict[str, Any]:
    """Genera una URL firmada (Presigned POST) para subir archivos directamente a Cloudflare R2 / S3."""
    storage_backend = STORAGE_BACKEND
    if storage_backend not in {'r2', 's3'}:
        raise RuntimeError(f'El backend de almacenamiento "{storage_backend}" no soporta cargas firmadas.')

    # Configuración de R2 / S3
    r2_bucket_name = os.environ.get('R2_BUCKET_NAME')
    r2_endpoint_url = os.environ.get('R2_ENDPOINT_URL')
    r2_account_id = os.environ.get('R2_ACCOUNT_ID')

    if not r2_bucket_name:
        raise RuntimeError('Falta configurar R2_BUCKET_NAME.')

    # Si es R2, el endpoint suele construirse con el Account ID si no se provee completo
    if not r2_endpoint_url and r2_account_id:
        r2_endpoint_url = f"https://{r2_account_id}.r2.cloudflarestorage.com"

    s3_client = _get_s3_client()
    if not s3_client:
        raise RuntimeError('No se pudo inicializar el cliente S3/R2.')

    object_name = f"covers/{uuid.uuid4()}-{nombre_archivo}"

    try:
        response = s3_client.generate_presigned_post(
            Bucket=r2_bucket_name,
            Key=object_name,
            Fields={'Content-Type': content_type},
            Conditions=[
                {'Content-Type': content_type},
                ['content-length-range', 0, max_upload_bytes]
            ],
            ExpiresIn=3600
        )
        # La URL final del objeto si la subida es exitosa
        from urllib.parse import quote
        quoted_object_name = quote(object_name)
        if r2_endpoint_url:
            # Para R2 o S3 con endpoint custom
            object_url = f"{r2_endpoint_url.rstrip('/')}/{r2_bucket_name}/{quoted_object_name}"
        else:
            object_url = f"https://{r2_bucket_name}.s3.amazonaws.com/{quoted_object_name}"

        response['object_url'] = object_url
        return response
    except Exception as e:
        raise RuntimeError(f"Error al generar presigned post: {str(e)}")


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
