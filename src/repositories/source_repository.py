"""
Repository para el modelo Source (fuentes de contenido).

Extiende BaseRepository con métodos específicos para buscar
y filtrar fuentes de contenido (canales YouTube, feeds RSS, etc.).
"""

from sqlalchemy.orm import Session

from src.models import Source
from src.repositories.base_repository import BaseRepository


class SourceRepository(BaseRepository[Source]):
    """
    Repository específico para el modelo Source.

    Hereda operaciones CRUD de BaseRepository y añade:
    - Búsqueda por URL (para evitar duplicados)
    - Filtrado por fuentes activas (para scraping)
    - Validación de existencia por URL
    """

    def __init__(self, session: Session):
        """
        Inicializa el repository con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy
        """
        super().__init__(session, Source)

    def get_by_url(self, url: str) -> Source | None:
        """
        Busca una fuente por su URL.

        Útil para validar duplicados antes de crear una nueva source.

        Args:
            url: URL de la fuente a buscar

        Returns:
            Source si existe, None si no existe

        Example:
            existing = repo.get_by_url("https://youtube.com/@DotCSV")
            if existing:
                raise AlreadyExistsError("Source", "url", url)
        """
        return self.session.query(Source).filter(Source.url == url).first()

    def get_active_sources(self) -> list[Source]:
        """
        Obtiene todas las fuentes activas.

        Las fuentes activas son las que deben ser scrapeadas
        periódicamente por el worker de Celery.

        Returns:
            Lista de sources con active=True

        Example:
            active_sources = repo.get_active_sources()
            for source in active_sources:
                scrape_task.delay(source.id)
        """
        return self.session.query(Source).filter(Source.active == True).all()  # noqa: E712

    def exists_by_url(self, url: str) -> bool:
        """
        Verifica si existe una fuente con la URL dada.

        Más eficiente que get_by_url() cuando solo necesitas
        validar existencia (no devuelve el objeto completo).

        Args:
            url: URL a verificar

        Returns:
            True si existe, False si no

        Example:
            if repo.exists_by_url(url):
                raise AlreadyExistsError("Source", "url", url)
        """
        return self.session.query(Source.id).filter(Source.url == url).first() is not None
