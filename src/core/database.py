"""
Configuración de SQLAlchemy para conexión a PostgreSQL.

Este módulo configura el engine de SQLAlchemy y proporciona
utilidades para crear sesiones de base de datos en los endpoints.

El engine es un singleton (se crea una sola vez).
Las sesiones se crean por request y se cierran automáticamente.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.core.config import settings

# Pool de conexiones ajustado para hardware modesto (i5-6500T, 8GB RAM)
# Cada conexión consume ~20-30MB. Con 5 conexiones base + 10 overflow = 450MB máximo
DB_POOL_SIZE = 5
DB_MAX_OVERFLOW = 10

engine = create_engine(
    str(settings.DATABASE_URL),
    pool_pre_ping=True,  # Previene errores de "conexión perdida" en conexiones idle
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    echo=settings.DEBUG,  # Loggea queries SQL en desarrollo para debugging
)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # Control explícito de transacciones (requerido por Repository Pattern)
    autoflush=False,  # Evita flush automático que puede causar queries inesperadas
    expire_on_commit=True,  # Fuerza recarga de objetos después de commit (previene stale data)
)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency de FastAPI que proporciona una sesión de base de datos.

    La sesión se cierra automáticamente al finalizar el request,
    incluso si ocurre una excepción.

    Uso en endpoints:
        @app.get("/sources")
        def get_sources(db: Session = Depends(get_db)):
            sources = db.query(Source).all()
            return sources

    Yields:
        Session: Sesión de SQLAlchemy para interactuar con la BD.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
