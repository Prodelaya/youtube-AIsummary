"""
Repository base genérico con CRUD para cualquier modelo SQLAlchemy.

Este repository implementa operaciones comunes (create, read, update, delete)
que todos los repositories específicos heredarán. Usa TypeVar para ser
reutilizable con cualquier modelo.
"""

from typing import Generic, TypeVar
from uuid import UUID

from sqlalchemy.orm import Session

from src.repositories.exceptions import NotFoundError

# TypeVar genérico para cualquier modelo SQLAlchemy
# Bound a 'object' significa que T puede ser cualquier clase
T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Repository base con operaciones CRUD genéricas.

    Uso:
        class SourceRepository(BaseRepository[Source]):
            def __init__(self, session: Session):
                super().__init__(session, Source)

    Atributos:
        session: Sesión de SQLAlchemy para queries
        model_class: Clase del modelo (Source, Video, etc.)
    """

    def __init__(self, session: Session, model_class: type[T]):
        """
        Inicializa el repository con sesión y clase de modelo.

        Args:
            session: Sesión activa de SQLAlchemy
            model_class: Clase del modelo (ej: Source, Video)
        """
        self.session = session
        self.model_class = model_class

    def create(self, entity: T) -> T:
        """
        Crea una nueva entidad en la base de datos.

        Args:
            entity: Instancia del modelo a crear

        Returns:
            La misma entidad con ID asignado y persistida

        Example:
            source = Source(name="DotCSV", url="https://...")
            created_source = repo.create(source)
            # created_source.id ahora tiene UUID asignado
        """
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)  # Obtiene valores generados (id, timestamps)
        return entity

    def get_by_id(self, entity_id: UUID) -> T:
        """
        Busca entidad por ID. Lanza excepción si no existe.

        Args:
            entity_id: UUID de la entidad

        Returns:
            Entidad encontrada

        Raises:
            NotFoundError: Si no existe entidad con ese ID
        """
        entity = self.session.get(self.model_class, entity_id)

        if entity is None:
            raise NotFoundError(resource_type=self.model_class.__name__, resource_id=entity_id)

        return entity

    def list_all(self, limit: int = 100, offset: int = 0) -> list[T]:
        """
        Lista entidades con paginación.

        Args:
            limit: Máximo de resultados (default 100)
            offset: Número de resultados a saltar (para paginación)

        Returns:
            Lista de entidades
        """
        return self.session.query(self.model_class).limit(limit).offset(offset).all()

    def update(self, entity: T) -> T:
        """
        Actualiza entidad existente en BD.

        Args:
            entity: Entidad modificada (debe tener ID)

        Returns:
            Entidad actualizada
        """
        self.session.commit()  # Persiste cambios del objeto
        self.session.refresh(entity)  # Recarga updated_at
        return entity

    def delete(self, entity: T) -> None:
        """
        Elimina entidad de la base de datos.

        Args:
            entity: Entidad a eliminar
        """
        self.session.delete(entity)
        self.session.commit()

    def exists(self, entity_id: UUID) -> bool:
        """
        Verifica si existe entidad con ese ID.

        Args:
            entity_id: UUID a verificar

        Returns:
            True si existe, False si no
        """
        return self.session.get(self.model_class, entity_id) is not None
