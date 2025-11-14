"""
Repository para el modelo Summary.

Extiende BaseRepository con métodos específicos para búsqueda
avanzada, filtrado por categoría/keywords y full-text search
en PostgreSQL.

Incluye integración con CacheService para optimizar queries frecuentes.
"""

import logging
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from src.models import Summary, Transcription, Video
from src.repositories.base_repository import BaseRepository

logger = logging.getLogger(__name__)


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

    def get_by_id(self, summary_id: UUID, use_cache: bool = True) -> Summary | None:
        """
        Obtiene resumen por ID con soporte de caché.

        Args:
            summary_id: UUID del resumen
            use_cache: Si True, intenta obtener de caché primero (default: True)

        Returns:
            Summary si existe, None si no existe

        Example:
            # Con caché
            summary = repo.get_by_id(summary_id)

            # Sin caché (forzar DB)
            summary = repo.get_by_id(summary_id, use_cache=False)
        """
        # Import lazy para evitar importación circular
        from src.services.cache_service import cache_service

        cache_key = f"summary:detail:{summary_id}"

        # Intentar obtener de caché
        if use_cache:
            cached_data = cache_service.get(cache_key, cache_type="summary")
            if cached_data:
                logger.debug(f"Cache hit for summary {summary_id}")
                # Reconstituir objeto Summary desde dict
                return Summary(**cached_data)

        # Cache miss o caché deshabilitado: consultar BD
        summary = self.session.query(Summary).filter(Summary.id == summary_id).first()

        if summary and use_cache:
            # Almacenar en caché (TTL: 24 horas)
            summary_dict = {
                "id": str(summary.id),
                "transcription_id": str(summary.transcription_id),
                "summary_text": summary.summary_text,
                "category": summary.category,
                "keywords": summary.keywords,
                "model_used": summary.model_used,
                "sent_to_telegram": summary.sent_to_telegram,
                "created_at": summary.created_at.isoformat() if summary.created_at else None,
                "sent_at": summary.sent_at.isoformat() if summary.sent_at else None,
            }
            cache_service.set(cache_key, summary_dict, ttl=86400, cache_type="summary")
            logger.debug(f"Cache set for summary {summary_id}")

        return summary

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

    def get_recent(self, limit: int = 10, with_relations: bool = False) -> list[Summary]:
        """
        Obtiene los resúmenes más recientes, ordenados por fecha de creación.

        Usado por el bot de Telegram en el comando /recent.

        Args:
            limit: Número máximo de resultados (default 10)
            with_relations: Si True, hace eager loading de video y source (default: False)

        Returns:
            Lista de resúmenes recientes, ordenados descendentemente

        Example:
            # Sin relaciones (más rápido)
            recent = repo.get_recent(limit=10)

            # Con relaciones cargadas (evita N+1 queries)
            recent = repo.get_recent(limit=10, with_relations=True)
            for summary in recent:
                print(summary.transcription.video.title)
        """
        query = self.session.query(Summary)

        # Eager loading de relaciones si se solicita
        if with_relations:
            query = query.options(
                joinedload(Summary.transcription)
                .joinedload(Transcription.video)
                .joinedload(Video.source)
            )

        return query.order_by(Summary.created_at.desc()).limit(limit).all()

    def search_by_text(self, query: str, limit: int = 20, use_cache: bool = True) -> list[Summary]:
        """
        Búsqueda full-text en el campo summary usando PostgreSQL.

        Usa el índice GIN creado en la migración para búsquedas eficientes.
        Soporta búsqueda en español (configuración 'spanish' en to_tsvector).
        Cachea resultados para queries frecuentes.

        Args:
            query: Texto a buscar (ej: "FastAPI python async")
            limit: Máximo de resultados (default 20)
            use_cache: Si True, intenta obtener de caché primero (default: True)

        Returns:
            Lista de resúmenes que coinciden con la búsqueda, ordenados por relevancia

        Example:
            # Con caché
            results = repo.search_by_text("FastAPI async", limit=10)

            # Sin caché (forzar búsqueda fresca)
            results = repo.search_by_text("FastAPI async", limit=10, use_cache=False)
        """
        # Import lazy para evitar importación circular
        from src.services.cache_service import cache_service, hash_query

        # Generar key de caché
        query_hash_str = hash_query(query)
        cache_key = f"search:{query_hash_str}:results:{limit}"

        # Intentar obtener de caché (solo IDs)
        if use_cache:
            cached_ids = cache_service.get(cache_key, cache_type="search")
            if cached_ids:
                logger.debug(f"Cache hit for search query: {query}")
                # Obtener resúmenes por IDs (usa caché individual de cada resumen)
                summaries = []
                for summary_id in cached_ids:
                    summary = self.get_by_id(UUID(summary_id), use_cache=True)
                    if summary:
                        summaries.append(summary)
                return summaries

        # Cache miss: ejecutar búsqueda
        summaries = (
            self.session.query(Summary)
            .filter(
                func.to_tsvector("spanish", Summary.summary_text).op("@@")(
                    func.plainto_tsquery("spanish", query)
                )
            )
            .limit(limit)
            .all()
        )

        if summaries and use_cache:
            # Cachear lista de IDs (TTL: 10 minutos)
            summary_ids = [str(s.id) for s in summaries]
            cache_service.set(cache_key, summary_ids, ttl=600, cache_type="search")
            logger.debug(f"Cache set for search query: {query} ({len(summary_ids)} results)")

            # Cachear resúmenes individuales si no están cacheados
            for summary in summaries:
                summary_cache_key = f"summary:detail:{summary.id}"
                if not cache_service.exists(summary_cache_key):
                    summary_dict = {
                        "id": str(summary.id),
                        "transcription_id": str(summary.transcription_id),
                        "summary_text": summary.summary_text,
                        "category": summary.category,
                        "keywords": summary.keywords,
                        "model_used": summary.model_used,
                        "sent_to_telegram": summary.sent_to_telegram,
                        "created_at": summary.created_at.isoformat() if summary.created_at else None,
                        "sent_at": summary.sent_at.isoformat() if summary.sent_at else None,
                    }
                    cache_service.set(summary_cache_key, summary_dict, ttl=86400, cache_type="summary")

        return summaries

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
                print(f"Category: {result['summary'].category}")
                print(f"Keywords: {result['summary'].keywords}")
        """

        # Crear vector de busqueda concatenando multiples campos existentes
        # Convertir el array de keywords a texto usando array_to_string
        search_vector = func.to_tsvector(
            "english",
            func.coalesce(Summary.summary_text, "")
            + " "
            + func.coalesce(func.array_to_string(Summary.keywords, " "), "")
            + " "
            + func.coalesce(Summary.category, ""),
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

        return [
            {"summary": summary, "relevance_score": float(score), "id": summary.id}
            for summary, score in results
        ]

    # ==================== MÉTODOS DE INVALIDACIÓN DE CACHÉ ====================

    def invalidate_summary_cache(self, summary_id: UUID) -> None:
        """
        Invalida caché de un resumen específico.

        Args:
            summary_id: UUID del resumen a invalidar

        Example:
            repo.invalidate_summary_cache(summary_id)
        """
        # Import lazy para evitar importación circular
        from src.services.cache_service import cache_service

        cache_key = f"summary:detail:{summary_id}"
        deleted = cache_service.delete(cache_key)

        logger.info(
            f"Invalidated cache for summary {summary_id}",
            extra={"summary_id": str(summary_id), "cache_deleted": deleted},
        )

    def invalidate_search_cache(self, keywords: list[str] | None = None) -> None:
        """
        Invalida caché de búsquedas.

        Args:
            keywords: Si se especifica, invalida solo búsquedas relacionadas.
                     Si es None, invalida todas las búsquedas.

        Example:
            # Invalidar búsquedas específicas
            repo.invalidate_search_cache(keywords=["fastapi", "python"])

            # Invalidar todas las búsquedas
            repo.invalidate_search_cache()
        """
        # Import lazy para evitar importación circular
        from src.services.cache_service import cache_service, hash_query

        if keywords:
            # Invalidar búsquedas específicas por keyword
            for keyword in keywords:
                query_hash_str = hash_query(keyword)
                pattern = f"search:{query_hash_str}:*"
                deleted_count = cache_service.invalidate_pattern(pattern)
                logger.debug(
                    f"Invalidated search cache for keyword '{keyword}'",
                    extra={"keyword": keyword, "deleted_count": deleted_count},
                )
        else:
            # Invalidar todas las búsquedas
            deleted_count = cache_service.invalidate_pattern("search:*:results:*")
            logger.info(
                "Invalidated all search cache",
                extra={"deleted_count": deleted_count},
            )

    def invalidate_recent_cache(self) -> None:
        """
        Invalida caché de listas de resúmenes recientes de todos los usuarios.

        Example:
            repo.invalidate_recent_cache()
        """
        # Import lazy para evitar importación circular
        from src.services.cache_service import cache_service

        deleted_count = cache_service.invalidate_pattern("user:*:recent")

        logger.info(
            "Invalidated all user recent cache",
            extra={"deleted_count": deleted_count},
        )
