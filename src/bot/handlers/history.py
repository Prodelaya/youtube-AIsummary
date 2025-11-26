"""
Handler del comando /recent - Historial de resúmenes recientes.

Muestra los últimos resúmenes de canales a los que el usuario está suscrito,
con formato rico y botón para ver transcripción completa.

Incluye caché para mejorar performance de queries frecuentes.
"""

import asyncio
import logging
from uuid import UUID

from sqlalchemy.orm import joinedload
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.ext import ContextTypes

from src.bot.utils.formatters import format_summary_message
from src.core.database import SessionLocal
from src.models import Source, Summary, Transcription, Video
from src.repositories.summary_repository import SummaryRepository
from src.repositories.telegram_user_repository import TelegramUserRepository
from src.services.cache_service import cache_service

logger = logging.getLogger(__name__)


# ==================== COMANDO /RECENT ====================


async def recent_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /recent.

    Workflow:
    1. Obtiene telegram_id del usuario
    2. Consulta últimos 10 resúmenes de canales suscritos
    3. Envía cada resumen con formato rico + botón "Ver transcripción"
    4. Maneja casos edge: sin suscripciones, sin resúmenes

    Args:
        update: Objeto de Telegram con info del mensaje
        context: Contexto del bot con datos de sesión

    Returns:
        None (envía mensajes directamente al usuario)
    """
    telegram_user = update.effective_user
    if not telegram_user:
        logger.warning("Comando /recent recibido sin effective_user")
        return

    telegram_id = telegram_user.id
    logger.info(
        f"Comando /recent solicitado por usuario {telegram_id}",
        extra={"telegram_id": telegram_id, "username": telegram_user.username},
    )

    try:
        # Obtener resúmenes recientes filtrados por suscripciones
        summaries = await asyncio.to_thread(_get_user_recent_summaries, telegram_id, limit=10)

        if not summaries:
            await update.message.reply_text(
                "📭 **No tienes resúmenes recientes**\n\n"
                "Posibles razones:\n"
                "• No estás suscrito a ningún canal (usa /sources)\n"
                "• Los canales suscritos aún no tienen contenido procesado\n\n"
                "Suscríbete a canales con /sources para empezar a recibir resúmenes.",
                parse_mode=ParseMode.MARKDOWN,
            )
            logger.info(
                f"Usuario {telegram_id} consultó /recent pero no tiene resúmenes disponibles"
            )
            return

        # Enviar header
        await update.message.reply_text(
            f"📚 **ÚLTIMOS RESÚMENES ({len(summaries)})**\n\n"
            "Aquí están los resúmenes más recientes de tus canales suscritos:",
            parse_mode=ParseMode.MARKDOWN,
        )

        # Enviar cada resumen con botón para ver transcripción
        for summary_data in summaries:
            summary = summary_data["summary"]
            video = summary_data["video"]
            source = summary_data["source"]

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
            f"Enviados {len(summaries)} resúmenes a usuario {telegram_id}",
            extra={
                "telegram_id": telegram_id,
                "summaries_count": len(summaries),
            },
        )

    except Exception as e:
        logger.error(
            f"Error al procesar /recent para usuario {telegram_id}: {e}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "error": str(e)},
        )
        await update.message.reply_text(
            "❌ Ocurrió un error al cargar el historial. Por favor intenta nuevamente."
        )


# ==================== CALLBACK HANDLER ====================


async def view_transcript_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja clicks en botón "Ver transcripción completa".

    Workflow:
    1. Parsea summary_id desde callback_data
    2. Obtiene transcripción completa desde BD
    3. Envía transcripción (dividida en chunks si es muy larga)
    4. Answer callback query con feedback

    Args:
        update: Objeto con callback_query
        context: Contexto del bot

    Returns:
        None (envía transcripción y answer callback)
    """
    query = update.callback_query
    telegram_user = update.effective_user

    if not query or not telegram_user:
        logger.warning("Callback view_transcript recibido sin query o effective_user")
        return

    telegram_id = telegram_user.id
    callback_data = query.data

    # Parsear summary_id desde callback_data (formato: "view_transcript:UUID")
    try:
        summary_id_str = callback_data.split(":", 1)[1]
        summary_id = UUID(summary_id_str)
    except (IndexError, ValueError):
        logger.error(
            f"Callback data inválido: {callback_data}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "callback_data": callback_data},
        )
        await query.answer("❌ Error al procesar la solicitud.", show_alert=True)
        return

    logger.info(
        f"Solicitud de transcripción: usuario {telegram_id} → resumen {summary_id}",
        extra={
            "telegram_id": telegram_id,
            "summary_id": str(summary_id),
        },
    )

    try:
        # Obtener transcripción completa
        transcription_text = await asyncio.to_thread(_get_transcription_by_summary_id, summary_id)

        if not transcription_text:
            await query.answer("⚠️ Transcripción no encontrada.", show_alert=True)
            logger.warning(
                f"Transcripción no encontrada para resumen {summary_id}",
                extra={"telegram_id": telegram_id, "summary_id": str(summary_id)},
            )
            return

        # Answer callback query primero (obligatorio)
        await query.answer("📄 Cargando transcripción...", show_alert=False)

        # Enviar transcripción (dividida en chunks si es necesaria)
        await _send_long_message(
            context=context,
            chat_id=telegram_user.id,
            text=transcription_text,
            max_length=4000,
        )

        logger.info(
            f"Transcripción enviada a usuario {telegram_id} (resumen {summary_id})",
            extra={
                "telegram_id": telegram_id,
                "summary_id": str(summary_id),
                "transcription_length": len(transcription_text),
            },
        )

    except Exception as e:
        logger.error(
            f"Error al procesar view_transcript para usuario {telegram_id}: {e}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "summary_id": str(summary_id), "error": str(e)},
        )
        await query.answer("❌ Error al cargar la transcripción.", show_alert=True)


# ==================== FUNCIONES AUXILIARES (SYNC) ====================


def _get_user_recent_summaries(telegram_id: int, limit: int) -> list[dict]:
    """
    Obtiene últimos resúmenes de canales suscritos por el usuario.

    Optimizado:
    - Filtrado en SQL (no en Python) para mejor performance
    - Caché de lista de summary IDs (TTL: 5 minutos)
    - Resúmenes individuales cacheados (TTL: 24 horas)

    Args:
        telegram_id: ID de Telegram del usuario
        limit: Número máximo de resúmenes a retornar

    Returns:
        Lista de dicts con keys: "summary", "video", "source"
        Ejemplo: [
            {
                "summary": Summary(...),
                "video": Video(...),
                "source": Source(...)
            },
            ...
        ]
    """
    # Key de caché para lista de IDs de resúmenes recientes del usuario
    cache_key = f"user:{telegram_id}:recent:{limit}"

    # Intentar obtener lista de IDs desde caché
    cached_summary_ids = cache_service.get(cache_key, cache_type="user_recent")

    session = SessionLocal()
    try:
        summary_repo = SummaryRepository(session)

        if cached_summary_ids:
            # Cache HIT: Obtener resúmenes por IDs (usa caché individual de cada resumen)
            logger.debug(f"Cache HIT for user {telegram_id} recent summaries")

            results = []
            for summary_id_str in cached_summary_ids:
                summary = summary_repo.get_by_id(UUID(summary_id_str), use_cache=True)
                if summary:
                    # Eager load relations
                    summary_with_relations = (
                        session.query(Summary)
                        .options(
                            joinedload(Summary.transcription)
                            .joinedload(Transcription.video)
                            .joinedload(Video.source)
                        )
                        .filter(Summary.id == summary.id)
                        .first()
                    )

                    if summary_with_relations:
                        video = summary_with_relations.transcription.video
                        source = video.source
                        results.append(
                            {
                                "summary": summary_with_relations,
                                "video": video,
                                "source": source,
                            }
                        )

            return results

        # Cache MISS: Consultar BD
        logger.debug(f"Cache MISS for user {telegram_id} recent summaries")

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

        # OPTIMIZACIÓN: Filtrar por suscripciones en SQL (no en Python)
        # Query directa con JOIN y filtro, sin buffer innecesario
        recent_summaries = (
            session.query(Summary)
            .join(Transcription, Summary.transcription_id == Transcription.id)
            .join(Video, Transcription.video_id == Video.id)
            .join(Source, Video.source_id == Source.id)
            .filter(Source.id.in_(subscribed_source_ids))  # Filtro SQL
            .order_by(Summary.created_at.desc())
            .limit(limit)  # Limit directo, sin buffer
            .options(
                # Eager loading para evitar N+1 en el loop
                joinedload(Summary.transcription)
                .joinedload(Transcription.video)
                .joinedload(Video.source)
            )
            .all()
        )

        # Construir lista de resultados (sin filtrado, ya viene filtrado de SQL)
        results = []
        summary_ids = []

        for summary in recent_summaries:
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

            summary_ids.append(str(summary.id))

            # Cachear resumen individual si no está cacheado
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

        # Cachear lista de IDs (TTL: 5 minutos)
        if summary_ids:
            cache_service.set(cache_key, summary_ids, ttl=300, cache_type="user_recent")
            logger.debug(
                f"Cached {len(summary_ids)} recent summary IDs for user {telegram_id}",
                extra={
                    "telegram_id": telegram_id,
                    "results_count": len(summary_ids),
                    "subscribed_sources": len(subscribed_source_ids),
                },
            )

        return results

    finally:
        session.close()


def _get_transcription_by_summary_id(summary_id: UUID) -> str | None:
    """
    Obtiene el texto de transcripción completo de un resumen.

    Args:
        summary_id: UUID del resumen

    Returns:
        str: Texto de la transcripción, o None si no existe
    """
    session = SessionLocal()
    try:
        SummaryRepository(session)

        # Obtener summary con eager loading de transcription
        summary = (
            session.query(Summary)
            .options(joinedload(Summary.transcription))
            .filter(Summary.id == summary_id)
            .first()
        )

        if not summary or not summary.transcription:
            return None

        return summary.transcription.transcription_text

    finally:
        session.close()


async def _send_long_message(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    text: str,
    max_length: int = 4000,
) -> None:
    """
    Envía mensaje largo dividiéndolo en chunks si excede max_length.

    Telegram tiene límite de 4096 caracteres por mensaje.
    Esta función divide el texto en chunks y envía múltiples mensajes.

    Args:
        context: Contexto del bot
        chat_id: ID del chat de destino
        text: Texto a enviar
        max_length: Longitud máxima por mensaje (default 4000)

    Returns:
        None (envía mensajes directamente)
    """
    if len(text) <= max_length:
        # Texto cabe en un solo mensaje
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"📄 **TRANSCRIPCIÓN COMPLETA**\n\n{text}",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    # Dividir en chunks
    chunks = []
    current_chunk = ""

    # Dividir por líneas para mantener integridad del texto
    lines = text.split("\n")

    for line in lines:
        # Si añadir esta línea excede el límite, guardar chunk actual
        if len(current_chunk) + len(line) + 1 > max_length:
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = line + "\n"
        else:
            current_chunk += line + "\n"

    # Añadir último chunk
    if current_chunk:
        chunks.append(current_chunk)

    # Enviar cada chunk
    for i, chunk in enumerate(chunks, start=1):
        header = f"📄 **TRANSCRIPCIÓN COMPLETA (parte {i}/{len(chunks)})**\n\n"
        await context.bot.send_message(
            chat_id=chat_id,
            text=header + chunk,
            parse_mode=ParseMode.MARKDOWN,
        )
