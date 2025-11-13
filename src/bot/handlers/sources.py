"""
Handler del comando /sources - Gestión de suscripciones interactivas.

Permite a los usuarios ver todos los canales disponibles y suscribirse/desuscribirse
mediante botones inline interactivos (✅/❌).
"""

import asyncio
import logging
from uuid import UUID

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from src.core.database import SessionLocal
from src.repositories.exceptions import AlreadyExistsError, NotFoundError
from src.repositories.source_repository import SourceRepository
from src.repositories.telegram_user_repository import TelegramUserRepository

logger = logging.getLogger(__name__)


# ==================== COMANDO /SOURCES ====================


async def sources_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /sources.

    Workflow:
    1. Obtiene todos los canales activos desde BD
    2. Verifica cuáles están suscritos por el usuario actual
    3. Genera teclado inline con botones ✅/❌ según estado
    4. Envía mensaje con teclado interactivo

    Args:
        update: Objeto de Telegram con info del mensaje
        context: Contexto del bot con datos de sesión

    Returns:
        None (envía mensaje directamente al usuario)
    """
    telegram_user = update.effective_user
    if not telegram_user:
        logger.warning("Comando /sources recibido sin effective_user")
        return

    telegram_id = telegram_user.id
    logger.info(
        f"Comando /sources solicitado por usuario {telegram_id}",
        extra={"telegram_id": telegram_id, "username": telegram_user.username},
    )

    try:
        # Obtener datos de BD (async wrapper)
        sources_data = await asyncio.to_thread(
            _get_sources_with_subscription_status, telegram_id
        )

        if not sources_data:
            await update.message.reply_text(
                "📭 **No hay canales disponibles actualmente.**\n\n"
                "El administrador aún no ha añadido fuentes de contenido.\n"
                "Vuelve a intentarlo más tarde.",
                parse_mode="Markdown",
            )
            logger.info(f"Usuario {telegram_id} consultó /sources pero no hay canales activos")
            return

        # Generar teclado inline
        keyboard = _build_sources_keyboard(sources_data)

        message_text = (
            "📺 **CANALES DISPONIBLES**\n\n"
            "Selecciona los canales que te interesan.\n"
            "Recibirás resúmenes automáticamente cuando publiquen contenido nuevo.\n\n"
            f"_Tus suscripciones activas: {sum(1 for _, subscribed in sources_data if subscribed)}/{len(sources_data)}_"
        )

        await update.message.reply_text(
            message_text, reply_markup=keyboard, parse_mode="Markdown"
        )

        logger.info(
            f"Teclado de fuentes enviado a usuario {telegram_id} ({len(sources_data)} canales)",
            extra={
                "telegram_id": telegram_id,
                "total_sources": len(sources_data),
                "subscribed_count": sum(1 for _, subscribed in sources_data if subscribed),
            },
        )

    except Exception as e:
        logger.error(
            f"Error al procesar /sources para usuario {telegram_id}: {e}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "error": str(e)},
        )
        await update.message.reply_text(
            "❌ Ocurrió un error al cargar los canales. Por favor intenta nuevamente.",
        )


# ==================== CALLBACK HANDLER ====================


async def toggle_subscription_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Maneja los clicks en botones del teclado inline (toggle de suscripciones).

    Workflow:
    1. Parsea source_id desde callback_data
    2. Alterna suscripción (subscribe/unsubscribe)
    3. Actualiza teclado inline para reflejar nuevo estado
    4. Envía feedback inmediato al usuario (answer_callback_query)

    Args:
        update: Objeto con callback_query
        context: Contexto del bot

    Returns:
        None (actualiza mensaje inline y envía answer)
    """
    query = update.callback_query
    telegram_user = update.effective_user

    if not query or not telegram_user:
        logger.warning("Callback recibido sin query o effective_user")
        return

    telegram_id = telegram_user.id
    callback_data = query.data

    # Parsear source_id desde callback_data (formato: "toggle_source:UUID")
    try:
        source_id_str = callback_data.split(":", 1)[1]
        source_id = UUID(source_id_str)
    except (IndexError, ValueError) as e:
        logger.error(
            f"Callback data inválido: {callback_data}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "callback_data": callback_data},
        )
        await query.answer("❌ Error al procesar la solicitud.", show_alert=True)
        return

    logger.info(
        f"Toggle de suscripción: usuario {telegram_id} → fuente {source_id}",
        extra={
            "telegram_id": telegram_id,
            "source_id": str(source_id),
            "callback_data": callback_data,
        },
    )

    try:
        # Ejecutar toggle en BD (async wrapper)
        result = await asyncio.to_thread(
            _toggle_user_subscription, telegram_id, source_id
        )

        # Actualizar teclado inline
        sources_data = await asyncio.to_thread(
            _get_sources_with_subscription_status, telegram_id
        )
        new_keyboard = _build_sources_keyboard(sources_data)

        # Actualizar texto del mensaje con el contador actualizado
        updated_message_text = (
            "📺 **CANALES DISPONIBLES**\n\n"
            "Selecciona los canales que te interesan.\n"
            "Recibirás resúmenes automáticamente cuando publiquen contenido nuevo.\n\n"
            f"_Tus suscripciones activas: {sum(1 for _, subscribed in sources_data if subscribed)}/{len(sources_data)}_"
        )

        await query.edit_message_text(
            text=updated_message_text,
            reply_markup=new_keyboard,
            parse_mode="Markdown"
        )

        # Feedback inmediato al usuario
        feedback_message = (
            f"✅ Suscrito a **{result['source_name']}**"
            if result["action"] == "subscribed"
            else f"❌ Desuscrito de **{result['source_name']}**"
        )

        await query.answer(feedback_message, show_alert=False)

        logger.info(
            f"Toggle completado: usuario {telegram_id} {result['action']} a {result['source_name']}",
            extra={
                "telegram_id": telegram_id,
                "source_id": str(source_id),
                "source_name": result["source_name"],
                "action": result["action"],
            },
        )

    except NotFoundError as e:
        logger.warning(
            f"Recurso no encontrado durante toggle: {e}",
            extra={"telegram_id": telegram_id, "source_id": str(source_id)},
        )
        await query.answer("⚠️ Canal no encontrado.", show_alert=True)

    except Exception as e:
        logger.error(
            f"Error al procesar toggle para usuario {telegram_id}: {e}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "source_id": str(source_id), "error": str(e)},
        )
        await query.answer("❌ Error al procesar la solicitud.", show_alert=True)


# ==================== FUNCIONES AUXILIARES (SYNC) ====================


def _get_sources_with_subscription_status(telegram_id: int) -> list[tuple[dict, bool]]:
    """
    Obtiene lista de fuentes activas con estado de suscripción del usuario.

    Args:
        telegram_id: ID de Telegram del usuario

    Returns:
        Lista de tuplas (source_dict, is_subscribed)
        Ejemplo: [
            ({"id": UUID, "name": "Fireship", ...}, True),
            ({"id": UUID, "name": "Midudev", ...}, False),
        ]
    """
    session = SessionLocal()
    try:
        user_repo = TelegramUserRepository(session)
        source_repo = SourceRepository(session)

        # Obtener usuario por telegram_id
        user = user_repo.get_by_telegram_id(telegram_id)
        if not user:
            logger.error(f"Usuario con telegram_id {telegram_id} no encontrado en BD")
            return []

        # Obtener todas las fuentes activas
        active_sources = source_repo.get_active_sources()

        if not active_sources:
            return []

        # Obtener suscripciones del usuario
        user_subscriptions = user_repo.get_user_subscriptions(user.id)
        subscribed_ids = {source.id for source in user_subscriptions}

        # Construir lista con estado de suscripción
        sources_data = []
        for source in active_sources:
            source_dict = {
                "id": source.id,
                "name": source.name,
                "url": source.url,
                "source_type": source.source_type,
            }
            is_subscribed = source.id in subscribed_ids
            sources_data.append((source_dict, is_subscribed))

        return sources_data

    finally:
        session.close()


def _toggle_user_subscription(telegram_id: int, source_id: UUID) -> dict:
    """
    Alterna suscripción del usuario a una fuente (subscribe/unsubscribe).

    Args:
        telegram_id: ID de Telegram del usuario
        source_id: UUID de la fuente

    Returns:
        dict con keys: "action" ("subscribed" | "unsubscribed"), "source_name"

    Raises:
        NotFoundError: Si usuario o fuente no existe
    """
    session = SessionLocal()
    try:
        user_repo = TelegramUserRepository(session)
        source_repo = SourceRepository(session)

        # Obtener usuario y fuente
        user = user_repo.get_by_telegram_id(telegram_id)
        if not user:
            raise NotFoundError("TelegramUser", telegram_id)

        source = source_repo.get_by_id(source_id)
        if not source:
            raise NotFoundError("Source", source_id)

        # Verificar estado actual de suscripción
        is_subscribed = user_repo.is_subscribed(user.id, source_id)

        # Toggle idempotente
        if is_subscribed:
            # Desuscribir
            try:
                user_repo.unsubscribe_from_source(user.id, source_id)
                action = "unsubscribed"
                logger.debug(f"Usuario {telegram_id} desuscrito de {source.name}")
            except NotFoundError:
                # Ya estaba desuscrito (race condition), no hacer nada
                action = "unsubscribed"
                logger.debug(f"Usuario {telegram_id} ya estaba desuscrito de {source.name}")
        else:
            # Suscribir
            try:
                user_repo.subscribe_to_source(user.id, source_id)
                action = "subscribed"
                logger.debug(f"Usuario {telegram_id} suscrito a {source.name}")
            except AlreadyExistsError:
                # Ya estaba suscrito (race condition), no hacer nada
                action = "subscribed"
                logger.debug(f"Usuario {telegram_id} ya estaba suscrito a {source.name}")

        return {"action": action, "source_name": source.name}

    finally:
        session.close()


def _build_sources_keyboard(
    sources_data: list[tuple[dict, bool]]
) -> InlineKeyboardMarkup:
    """
    Construye teclado inline con botones de suscripción.

    Args:
        sources_data: Lista de tuplas (source_dict, is_subscribed)

    Returns:
        InlineKeyboardMarkup con botones configurados
    """
    keyboard = []

    for source_dict, is_subscribed in sources_data:
        emoji = "✅" if is_subscribed else "❌"
        button_text = f"{emoji} {source_dict['name']}"
        callback_data = f"toggle_source:{source_dict['id']}"

        # Crear botón
        button = InlineKeyboardButton(text=button_text, callback_data=callback_data)

        # Añadir fila (un botón por fila para mejor UX móvil)
        keyboard.append([button])

    return InlineKeyboardMarkup(keyboard)
