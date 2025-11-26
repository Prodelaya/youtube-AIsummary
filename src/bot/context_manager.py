"""
Context manager para Bot de Telegram con Request ID y logging estructurado.

Este módulo proporciona utilities para enriquecer el contexto de logging
en handlers del bot, usando el update_id de Telegram como Request ID natural.

Example:
    >>> from src.bot.context_manager import bot_update_context
    >>> async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    >>>     with bot_update_context(update, command="start"):
    >>>         logger.info("user_started_bot")
"""

import time
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import structlog
from telegram import Update

from src.core.logging_config import get_logger

logger = get_logger(__name__)


@contextmanager
def bot_update_context(update: Update, **context_vars: Any) -> Generator[None, None, None]:
    """
    Context manager para inyectar contexto en logs de handlers del bot.

    Usa el update_id de Telegram como Request ID natural para correlación.
    Añade información del usuario y chat automáticamente.

    Args:
        update: Update de Telegram.
        **context_vars: Variables adicionales de contexto (command, callback_data, etc.).

    Yields:
        None

    Example:
        >>> async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        >>>     with bot_update_context(update, command="start"):
        >>>         logger.info("user_started_bot")
        >>>         # Log incluirá: request_id (update_id), user_id, chat_id, command
    """
    # Extraer información del update
    request_id = f"tg-{update.update_id}"
    user_id = update.effective_user.id if update.effective_user else None
    chat_id = update.effective_chat.id if update.effective_chat else None
    username = update.effective_user.username if update.effective_user else None

    # Preparar contexto completo
    full_context = {
        "request_id": request_id,
        "user_id": user_id,
        "chat_id": chat_id,
        "username": username,
        **context_vars,
    }

    # Inyectar en structlog
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**full_context)

    # Logging de inicio de handler
    start_time = time.time()

    logger.info(
        "bot_update_received",
        **context_vars,
    )

    try:
        yield

        # Logging de finalización exitosa
        duration_ms = int((time.time() - start_time) * 1000)

        logger.info(
            "bot_update_handled",
            duration_ms=duration_ms,
            **context_vars,
        )

    except Exception as exc:
        # Logging de error
        duration_ms = int((time.time() - start_time) * 1000)

        logger.error(
            "bot_update_failed",
            error=str(exc),
            error_type=type(exc).__name__,
            duration_ms=duration_ms,
            exc_info=True,
            **context_vars,
        )

        raise

    finally:
        # Limpiar contexto
        structlog.contextvars.clear_contextvars()


def bind_bot_context(**context_vars: Any) -> None:
    """
    Bind adicional de variables al contexto actual del bot.

    Args:
        **context_vars: Variables de contexto a añadir.

    Example:
        >>> with bot_update_context(update, command="search"):
        >>>     query = update.message.text
        >>>     bind_bot_context(search_query=query)
        >>>     logger.info("search_executed")
    """
    structlog.contextvars.bind_contextvars(**context_vars)
