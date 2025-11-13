"""
Bot de Telegram - Configuración principal.

Este módulo inicializa y arranca el bot de Telegram en modo polling.
Registra todos los handlers de comandos y configura el logging.

Para ejecutar:
    poetry run python -m src.bot.telegram_bot
"""

import logging
from typing import NoReturn

from telegram import BotCommand, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes

from src.bot.handlers import (
    help_handler,
    sources_handler,
    start_handler,
    toggle_subscription_callback,
)
from src.core.config import settings

# ==================== LOGGING ====================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

# Reducir verbosidad de librerías externas
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("telegram").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


# ==================== ERROR HANDLER ====================


async def error_handler(update: Update | None, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja errores globales del bot.

    Loggea el error completo y notifica al usuario si es posible.

    Args:
        update: Update que causó el error (puede ser None)
        context: Contexto con información del error

    Returns:
        None
    """
    logger.error(
        f"Error no manejado: {context.error}",
        exc_info=context.error,
        extra={
            "update": update.to_dict() if update else None,
            "error_type": type(context.error).__name__,
        },
    )

    # Intentar notificar al usuario
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Ocurrió un error inesperado. El equipo técnico ha sido notificado.\n"
                "Por favor intenta nuevamente en unos momentos."
            )
        except Exception as e:
            logger.error(f"No se pudo enviar mensaje de error al usuario: {e}")


# ==================== INICIALIZACIÓN DEL BOT ====================


def create_application() -> Application:
    """
    Crea y configura la aplicación del bot.

    Returns:
        Application configurada con todos los handlers registrados
    """
    # Crear aplicación con el token del bot
    application = Application.builder().token(settings.TELEGRAM_BOT_TOKEN).build()

    # Registrar handlers de comandos
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("sources", sources_handler))

    # Registrar callback query handlers (botones inline)
    application.add_handler(
        CallbackQueryHandler(toggle_subscription_callback, pattern="^toggle_source:")
    )

    # Registrar error handler global
    application.add_error_handler(error_handler)

    logger.info("Aplicación del bot configurada exitosamente")
    return application


async def post_init(application: Application) -> None:
    """
    Ejecuta tareas de inicialización después de crear la app.

    Configura los comandos del bot que aparecen en el menú de Telegram.

    Args:
        application: Aplicación del bot ya inicializada

    Returns:
        None
    """
    # Configurar comandos del bot (aparecen en el menú de Telegram)
    commands = [
        BotCommand("start", "Iniciar el bot y registrarse"),
        BotCommand("help", "Ver comandos disponibles"),
        BotCommand("sources", "Gestionar suscripciones a canales"),
        BotCommand("recent", "Ver últimos resúmenes (próximamente)"),
        BotCommand("search", "Buscar en histórico (próximamente)"),
    ]

    await application.bot.set_my_commands(commands)
    logger.info(f"Comandos del bot configurados: {[cmd.command for cmd in commands]}")

    # Obtener info del bot
    bot_info = await application.bot.get_me()
    logger.info(
        f"Bot inicializado: @{bot_info.username} (ID: {bot_info.id})",
        extra={
            "bot_username": bot_info.username,
            "bot_id": bot_info.id,
            "bot_name": bot_info.first_name,
        },
    )


# ==================== MAIN ====================


def start_bot() -> NoReturn:
    """
    Arranca el bot en modo polling (desarrollo).

    Este método bloquea el hilo principal hasta que se detenga el bot (Ctrl+C).

    Returns:
        NoReturn (bloquea hasta interrupción manual)
    """
    logger.info("Iniciando bot de Telegram en modo POLLING...")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    # Crear aplicación
    application = create_application()

    # Configurar post-init
    application.post_init = post_init

    # Arrancar bot en modo polling
    logger.info("Bot arrancado. Presiona Ctrl+C para detener.")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,  # Recibir todos los tipos de updates
        drop_pending_updates=True,  # Ignorar mensajes pendientes al arrancar
    )


if __name__ == "__main__":
    start_bot()
