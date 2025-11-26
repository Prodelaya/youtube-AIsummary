"""
Handler del comando /search - Búsqueda en historial de resúmenes.

Permite buscar en resúmenes pasados usando keywords, filtrado por
suscripciones del usuario.

Incluye caché optimizado para búsquedas frecuentes.
"""

import asyncio
import logging

from sqlalchemy.orm import joinedload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.bot.utils.formatters import format_summary_message
from src.core.database import SessionLocal
from src.models import Source, Summary, Transcription, Video
from src.repositories.telegram_user_repository import TelegramUserRepository

logger = logging.getLogger(__name__)


# Límites de validación
MIN_QUERY_LENGTH = 3
MAX_QUERY_LENGTH = 100
MAX_RESULTS_TO_SHOW = 10


# ==================== COMANDO /SEARCH ====================


async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /search <query>.

    Workflow:
    1. Valida argumentos (mínimo 3 chars, máximo 100 chars)
    2. Busca en resúmenes usando full-text search de PostgreSQL
    3. Filtra resultados por suscripciones del usuario
    4. Envía resultados con formato rico + botón "Ver transcripción"
    5. Maneja casos edge: query vacía, sin resultados, query muy corta

    Args:
        update: Objeto de Telegram con info del mensaje
        context: Contexto del bot con datos de sesión

    Returns:
        None (envía mensajes directamente al usuario)
    """
    telegram_user = update.effective_user
    if not telegram_user:
        logger.warning("Comando /search recibido sin effective_user")
        return

    telegram_id = telegram_user.id

    # Validar que hay argumentos
    if not context.args:
        await update.message.reply_text(
            "❓ **Uso del comando /search**\n\n"
            "**Sintaxis:** `/search <keywords>`\n\n"
            "**Ejemplos:**\n"
            "• `/search FastAPI`\n"
            "• `/search Python async`\n"
            "• `/search machine learning`\n\n"
            "**Nota:** La búsqueda debe tener al menos 3 caracteres.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Construir query string
    query = " ".join(context.args)

    # Validar longitud de query
    if len(query) < MIN_QUERY_LENGTH:
        await update.message.reply_text(
            f"⚠️ **Query muy corta**\n\n"
            f"La búsqueda debe tener al menos {MIN_QUERY_LENGTH} caracteres.\n"
            f"Tu búsqueda: `{query}` ({len(query)} caracteres)\n\n"
            f"Ejemplo válido: `/search FastAPI`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Truncar query si es muy larga
    if len(query) > MAX_QUERY_LENGTH:
        original_query = query
        query = query[:MAX_QUERY_LENGTH]
        logger.info(
            f"Query truncada de {len(original_query)} a {MAX_QUERY_LENGTH} chars",
            extra={
                "telegram_id": telegram_id,
                "original_length": len(original_query),
                "truncated_query": query,
            },
        )

    logger.info(
        f"Búsqueda solicitada: '{query}' por usuario {telegram_id}",
        extra={
            "telegram_id": telegram_id,
            "username": telegram_user.username,
            "query": query,
        },
    )

    try:
        # Realizar búsqueda filtrada por suscripciones
        results = await asyncio.to_thread(
            _search_user_summaries, telegram_id, query, limit=50  # Buffer para filtrar
        )

        if not results:
            await update.message.reply_text(
                f"🔍 **No se encontraron resultados para '{query}'**\n\n"
                "**Sugerencias:**\n"
                "• Intenta con otros términos de búsqueda\n"
                "• Verifica tus suscripciones con /sources\n"
                "• Usa palabras clave más generales\n\n"
                "**Ejemplo:** En lugar de `FastAPI routing`, prueba `FastAPI`",
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info(
                f"Búsqueda sin resultados: '{query}' para usuario {telegram_id}",
                extra={"telegram_id": telegram_id, "query": query},
            )
            return

        # Limitar resultados mostrados
        total_results = len(results)
        results_to_show = results[:MAX_RESULTS_TO_SHOW]

        # Enviar header con count
        header_text = (
            f"🔍 **RESULTADOS DE BÚSQUEDA**\n\n"
            f"**Query:** `{query}`\n"
            f"**Encontrados:** {total_results} resúmenes\n"
        )

        if total_results > MAX_RESULTS_TO_SHOW:
            header_text += (
                f"**Mostrando:** Primeros {MAX_RESULTS_TO_SHOW} resultados\n\n"
                f"💡 _Refina tu búsqueda para mejores resultados_"
            )

        await update.message.reply_text(header_text, parse_mode=ParseMode.MARKDOWN)

        # Enviar cada resultado con botón para ver transcripción
        for result_data in results_to_show:
            summary = result_data["summary"]
            video = result_data["video"]
            source = result_data["source"]

            # Formatear mensaje
            message_text = format_summary_message(summary, video, source)

            # Crear botón inline para ver transcripción
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text="📄 Ver transcripción completa",
                            callback_data=f"view_transcript:{summary.id}",
                        )
                    ]
                ]
            )

            # Enviar mensaje
            await update.message.reply_text(
                message_text,
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=keyboard,
                disable_web_page_preview=False,
            )

        logger.info(
            f"Enviados {len(results_to_show)} resultados a usuario {telegram_id} (query: '{query}')",
            extra={
                "telegram_id": telegram_id,
                "query": query,
                "total_results": total_results,
                "shown_results": len(results_to_show),
            },
        )

    except Exception as e:
        logger.error(
            f"Error al procesar /search para usuario {telegram_id}: {e}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "query": query, "error": str(e)},
        )
        await update.message.reply_text(
            "❌ Ocurrió un error al realizar la búsqueda. Por favor intenta nuevamente."
        )


# ==================== FUNCIONES AUXILIARES (SYNC) ====================


def _search_user_summaries(telegram_id: int, query: str, limit: int) -> list[dict]:
    """
    Busca en resúmenes usando full-text search, filtrado por suscripciones.

    Optimizado: Filtrado en SQL (no en Python) para mejor performance.

    Args:
        telegram_id: ID de Telegram del usuario
        query: Términos de búsqueda
        limit: Número máximo de resultados a retornar

    Returns:
        Lista de dicts con keys: "summary", "video", "source"
        Ordenados por relevancia/fecha
    """
    session = SessionLocal()
    try:
        user_repo = TelegramUserRepository(session)

        # Obtener usuario por telegram_id
        user = user_repo.get_by_telegram_id(telegram_id)
        if not user:
            logger.warning(f"Usuario con telegram_id {telegram_id} no encontrado en BD")
            return []

        # Obtener suscripciones del usuario
        user_subscriptions = user_repo.get_user_subscriptions(user.id)
        if not user_subscriptions:
            logger.info(f"Usuario {telegram_id} no tiene suscripciones activas")
            return []

        subscribed_source_ids = [source.id for source in user_subscriptions]

        # Sanitizar query (básico: eliminar caracteres especiales SQL)
        sanitized_query = _sanitize_query(query)

        # OPTIMIZACIÓN: Búsqueda full-text con filtro de suscripciones en SQL
        from sqlalchemy import func

        search_results = (
            session.query(Summary)
            .join(Transcription, Summary.transcription_id == Transcription.id)
            .join(Video, Transcription.video_id == Video.id)
            .join(Source, Video.source_id == Source.id)
            .filter(Source.id.in_(subscribed_source_ids))  # Filtro SQL de suscripciones
            .filter(
                # Full-text search
                func.to_tsvector("spanish", Summary.summary_text).op("@@")(
                    func.plainto_tsquery("spanish", sanitized_query)
                )
            )
            .order_by(Summary.created_at.desc())
            .limit(limit)
            .options(
                # Eager loading para evitar N+1
                joinedload(Summary.transcription)
                .joinedload(Transcription.video)
                .joinedload(Video.source)
            )
            .all()
        )

        if not search_results:
            return []

        # Construir lista de resultados (sin filtrado, ya viene filtrado de SQL)
        results = []
        for summary in search_results:
            # Las relaciones ya están cargadas por eager loading
            video = summary.transcription.video
            source = video.source

            results.append(
                {
                    "summary": summary,
                    "video": video,
                    "source": source,
                }
            )

        logger.debug(
            f"Search returned {len(results)} results for user {telegram_id}",
            extra={
                "telegram_id": telegram_id,
                "query": sanitized_query,
                "results_count": len(results),
                "subscribed_sources": len(subscribed_source_ids),
            },
        )

        return results

    finally:
        session.close()


def _sanitize_query(query: str) -> str:
    """
    Sanitiza query de búsqueda para prevenir inyección SQL.

    Args:
        query: Query de búsqueda original

    Returns:
        str: Query sanitizada
    """
    # Eliminar caracteres especiales problemáticos
    # PostgreSQL full-text search ya maneja la mayoría de casos
    # pero eliminamos caracteres que podrían causar errores

    # Eliminar caracteres de control y especiales SQL
    forbidden_chars = [";", "'", '"', "\\", "--", "/*", "*/", "xp_", "sp_"]

    sanitized = query
    for char in forbidden_chars:
        sanitized = sanitized.replace(char, " ")

    # Normalizar espacios múltiples
    sanitized = " ".join(sanitized.split())

    return sanitized.strip()
