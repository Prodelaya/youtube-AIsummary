"""
Handler del comando /start.

Registra automáticamente al usuario en la base de datos y envía mensaje de bienvenida.
El registro es idempotente (si el usuario ya existe, no duplica).
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes

from src.core.database import SessionLocal
from src.models.telegram_user import TelegramUser
from src.repositories.telegram_user_repository import TelegramUserRepository

logger = logging.getLogger(__name__)


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /start.

    Workflow:
    1. Extrae datos del usuario desde el update de Telegram
    2. Registra o actualiza usuario en BD (idempotente)
    3. Envía mensaje de bienvenida personalizado

    Args:
        update: Objeto de Telegram con info del mensaje
        context: Contexto del bot con datos de sesión

    Returns:
        None (envía mensaje directamente al usuario)
    """
    # Extraer datos del usuario
    telegram_user = update.effective_user
    if not telegram_user:
        logger.warning("Comando /start recibido sin effective_user")
        return

    telegram_id = telegram_user.id
    username = telegram_user.username
    first_name = telegram_user.first_name or "Usuario"

    logger.info(
        f"Comando /start de usuario: {telegram_id} (@{username})",
        extra={
            "telegram_id": telegram_id,
            "username": username,
            "first_name": first_name,
        },
    )

    # Registrar usuario en BD (async wrapper con asyncio.to_thread)
    try:
        user_created = await asyncio.to_thread(
            _create_or_update_user, telegram_id, username, first_name
        )

        # Mensaje de bienvenida personalizado
        welcome_message = f"""👋 ¡Hola **{first_name}**!

Bienvenido a **IA Monitor**, tu bot personal para descubrir contenido sobre IA y programación.

🎯 **¿Qué puedo hacer por ti?**
• Resumir videos de YouTube sobre IA
• Transcribir podcasts y charlas técnicas
• Enviarte resúmenes personalizados de tus canales favoritos

📋 **Comandos disponibles:**
/help - Ver todos los comandos
/sources - Gestionar tus suscripciones
/recent - Ver últimos resúmenes
/search - Buscar en tu histórico

{"🆕 Usuario registrado correctamente." if user_created else "✅ Ya estabas registrado, ¡bienvenido de nuevo!"}

💡 **Tip:** Empieza con /sources para elegir tus canales de interés.
"""

        await update.message.reply_text(welcome_message, parse_mode="Markdown")
        logger.info(f"Usuario {telegram_id} procesado exitosamente (nuevo={user_created})")

    except Exception as e:
        logger.error(
            f"Error al procesar /start para usuario {telegram_id}: {e}",
            exc_info=True,
            extra={"telegram_id": telegram_id, "error": str(e)},
        )
        await update.message.reply_text(
            "❌ Ocurrió un error al procesar tu solicitud. Por favor intenta nuevamente.",
        )


def _create_or_update_user(telegram_id: int, username: str | None, first_name: str) -> bool:
    """
    Crea o actualiza usuario en BD (función síncrona para usar con asyncio.to_thread).

    Args:
        telegram_id: ID único de Telegram del usuario
        username: Username de Telegram (puede ser None)
        first_name: Nombre del usuario

    Returns:
        True si el usuario fue creado, False si ya existía
    """
    session = SessionLocal()
    try:
        repo = TelegramUserRepository(session)

        # Verificar si usuario ya existe
        existing_user = repo.get_by_telegram_id(telegram_id)

        if existing_user:
            # Usuario existente: actualizar datos por si cambió username/nombre
            existing_user.username = username
            existing_user.first_name = first_name
            existing_user.is_active = True  # Reactivar si estaba inactivo
            session.commit()
            logger.debug(f"Usuario {telegram_id} actualizado")
            return False
        else:
            # Usuario nuevo: crear instancia del modelo
            new_user = TelegramUser(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                is_active=True,
            )
            # Persistir en BD usando el repository
            repo.create(new_user)
            session.commit()
            logger.info(f"Usuario nuevo creado: {telegram_id} (@{username})")
            return True
    finally:
        session.close()
