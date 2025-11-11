"""
Repository para el modelo Summary.

Extiende BaseRepository con métodos específicos para búsqueda
avanzada, filtrado por categoría/keywords y full-text search
en PostgreSQL.
"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from src.models import Summary
from src.repositories.base_repository import BaseRepository


class SummaryRepository(BaseRepository[Summary]):
    """
    Repository específico para el modelo Summary.

    Hereda operaciones CRUD de BaseRepository y añade:
    - Búsqueda por transcription_id (relación 1:1)
    - Full-text search en campo summary (usando PostgreSQL)
    - Filtrado por categoría (framework, language, tool, concept)
    - Filtrado por keywords (array search)
    - Queries para Telegram bot (recientes, búsqueda)
    """

    def __init__(self, session: Session):
        """
        Inicializa el repository con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy
        """
        super().__init__(session, Summary)

    def get_by_transcription_id(self, transcription_id: UUID) -> Summary | None:
        """
        Busca el resumen de una transcripción específica.

        Como la relación es 1:1, solo puede haber un resumen por transcripción.

        Args:
            transcription_id: UUID de la transcripción

        Returns:
            Summary si existe, None si la transcripción no tiene resumen

        Example:
            summary = repo.get_by_transcription_id(transcription_id)
            if summary:
                send_to_telegram(summary)
        """
        return (
            self.session.query(Summary).filter(Summary.transcription_id == transcription_id).first()
        )

    def get_recent(self, limit: int = 10) -> list[Summary]:
        """
        Obtiene los resúmenes más recientes, ordenados por fecha de creación.

        Usado por el bot de Telegram en el comando /recent.

        Args:
            limit: Número máximo de resultados (default 10)

        Returns:
            Lista de resúmenes recientes, ordenados descendentemente

        Example:
            recent = repo.get_recent(limit=10)
            for summary in recent:
                bot.send_message(chat_id, summary.summary)
        """
        return self.session.query(Summary).order_by(Summary.created_at.desc()).limit(limit).all()

    def search_by_text(self, query: str, limit: int = 20) -> list[Summary]:
        """
        Búsqueda full-text en el campo summary usando PostgreSQL.

        Usa el índice GIN creado en la migración para búsquedas eficientes.
        Soporta búsqueda en español (configuración 'spanish' en to_tsvector).

        Args:
            query: Texto a buscar (ej: "FastAPI python async")
            limit: Máximo de resultados (default 20)

        Returns:
            Lista de resúmenes que coinciden con la búsqueda, ordenados por relevancia

        Example:
            results = repo.search_by_text("FastAPI async", limit=10)
        """
        return (
            self.session.query(Summary)
            .filter(
                func.to_tsvector("spanish", Summary.summary_text).op("@@")(
                    func.plainto_tsquery("spanish", query)
                )
            )
            .limit(limit)
            .all()
        )

    def get_by_category(self, category: str) -> list[Summary]:
        """
        Obtiene resúmenes filtrados por categoría.

        Args:
            category: Categoría a filtrar ("framework", "language", "tool", "concept")

        Returns:
            Lista de resúmenes de esa categoría

        Example:
            frameworks = repo.get_by_category("framework")
        """
        return self.session.query(Summary).filter(Summary.category == category).all()

    def search_by_keyword(self, keyword: str) -> list[Summary]:
        """
        Busca resúmenes que contienen un keyword específico.

        El campo keywords es un array de strings, usa operador ANY de PostgreSQL.

        Args:
            keyword: Keyword a buscar (ej: "fastapi", "python", "docker")

        Returns:
            Lista de resúmenes que contienen ese keyword

        Example:
            fastapi_summaries = repo.search_by_keyword("fastapi")
        """
        # Usar SQL raw con ANY de PostgreSQL
        # Sintaxis SQL: :keyword = ANY(keywords)
        from sqlalchemy import text

        return (
            self.session.query(Summary)
            .filter(text(":keyword = ANY(keywords)"))
            .params(keyword=keyword)
            .all()
        )

    def get_unsent_to_telegram(self) -> list[Summary]:
        """
        Obtiene resúmenes que aún no han sido enviados a Telegram.

        Usado por el worker de distribución para saber qué resúmenes enviar.

        Returns:
            Lista de resúmenes con sent_to_telegram=False

        Example:
            unsent = repo.get_unsent_to_telegram()
            for summary in unsent:
                distribute_task.delay(summary.id)
        """
        return (
            self.session.query(Summary)
            .filter(Summary.sent_to_telegram == False)  # noqa: E712
            .all()
        )

    def mark_as_sent(self, summary_id: UUID) -> None:
        """
        Marca un resumen como enviado a Telegram.

        Actualiza sent_to_telegram=True y sent_at con timestamp actual.

        Args:
            summary_id: UUID del resumen

        Example:
            repo.mark_as_sent(summary_id)
        """
        summary = self.get_by_id(summary_id)
        summary.sent_to_telegram = True
        summary.sent_at = func.now()
        self.session.commit()

    def list_paginated(
        self,
        limit: int = 20,
        cursor: UUID | None = None,
    ) -> list[Summary]:
        """
        Lista resumenes con paginacion cursor-based.

        Args:
            limit: Numero maximo de resumenes a retornar.
            cursor: UUID del ultimo resumen (para paginacion).

        Returns:
            Lista de resumenes ordenados por created_at DESC.

        Example:
            # Primera pagina
            summaries = repo.list_paginated(limit=20)

            # Segunda pagina
            last_id = summaries[-1].id
            next_summaries = repo.list_paginated(limit=20, cursor=last_id)
        """
        query = self.session.query(Summary)

        # Paginacion cursor-based
        if cursor:
            cursor_summary = self.session.query(Summary).filter(Summary.id == cursor).first()
            if cursor_summary:
                query = query.filter(Summary.created_at < cursor_summary.created_at)

        # Ordenar y limitar
        query = query.order_by(Summary.created_at.desc()).limit(limit)

        return query.all()

    def get_by_video_id(self, video_id: UUID) -> Summary | None:
        """
        Busca el resumen de un video especifico.

        Navega a traves de la relacion video -> transcription -> summary.

        Args:
            video_id: UUID del video.

        Returns:
            Summary si existe, None si el video no tiene resumen.

        Example:
            summary = repo.get_by_video_id(video_id)
            if summary:
                return summary.summary_text
        """
        from src.models import Transcription

        # Join con Transcription para filtrar por video_id
        return (
            self.session.query(Summary)
            .join(Transcription, Summary.transcription_id == Transcription.id)
            .filter(Transcription.video_id == video_id)
            .first()
        )

    def search_full_text(
        self,
        query: str,
        limit: int = 20,
        cursor: UUID | None = None,
    ) -> list[dict]:
        """
        Busqueda full-text avanzada con ranking de relevancia.

        Busca en title, summary_text, key_points y topics.
        Retorna resultados ordenados por relevancia con score.

        Args:
            query: Terminos de busqueda.
            limit: Numero maximo de resultados.
            cursor: UUID del ultimo resultado (para paginacion).

        Returns:
            Lista de diccionarios con 'summary' y 'relevance_score'.

        Example:
            results = repo.search_full_text("machine learning", limit=20)
            for result in results:
                print(f"Score: {result['relevance_score']}")
                print(f"Title: {result['summary'].title}")
        """
        from sqlalchemy import cast, String

        # Crear vector de busqueda concatenando multiples campos
        search_vector = func.to_tsvector(
            "english",
            func.coalesce(Summary.title, "")
            + " "
            + func.coalesce(Summary.summary_text, "")
            + " "
            + func.coalesce(cast(Summary.key_points, String), "")
            + " "
            + func.coalesce(cast(Summary.topics, String), ""),
        )

        # Query de busqueda
        search_query = func.plainto_tsquery("english", query)

        # Calcular ranking de relevancia
        rank = func.ts_rank(search_vector, search_query).label("relevance_score")

        query_obj = (
            self.session.query(Summary, rank)
            .filter(search_vector.op("@@")(search_query))
            .order_by(rank.desc())
        )

        # Paginacion cursor-based
        if cursor:
            cursor_summary = self.session.query(Summary).filter(Summary.id == cursor).first()
            if cursor_summary:
                # Calcular rank del cursor
                cursor_rank = (
                    self.session.query(rank)
                    .filter(Summary.id == cursor)
                    .filter(search_vector.op("@@")(search_query))
                    .scalar()
                )
                if cursor_rank:
                    query_obj = query_obj.filter(rank < cursor_rank)

        results = query_obj.limit(limit).all()

        return [{"summary": summary, "relevance_score": float(score), "id": summary.id} for summary, score in results]
