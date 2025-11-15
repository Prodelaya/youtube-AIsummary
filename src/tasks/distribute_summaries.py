"""
Tareas de Celery para distribución de resúmenes a usuarios vía Telegram.

Este módulo contiene tareas asíncronas para enviar resúmenes generados
a todos los usuarios suscritos al canal correspondiente.

Tareas:
- distribute_summary_task: Distribuye un resumen a usuarios suscritos

Características:
- Idempotencia: ejecutar 2 veces = mismo resultado
- Manejo de errores: usuarios que bloquearon el bot, rate limits, etc.
- Rate limiting: respeta límites de Telegram (30 msg/seg)
- Logging estructurado con contexto del resumen
"""

import asyncio
from datetime import datetime, timezone
from uuid import UUID

from celery import Task
from sqlalchemy.orm import Session
from telegram import Bot
from telegram.error import Forbidden, TelegramError

from src.bot.utils.formatters import format_summary_message
from src.core.celery_app import celery_app
from src.core.celery_context import task_context
from src.core.config import settings
from src.core.database import SessionLocal
from src.core.logging_config import get_logger
from src.repositories.summary_repository import SummaryRepository
from src.repositories.telegram_user_repository import TelegramUserRepository

# ==================== LOGGER ====================

logger = get_logger(__name__)


# ==================== CUSTOM TASK BASE ====================


class DatabaseTask(Task):
    """
    Task base customizada que maneja sesiones de BD automáticamente.

    Garantiza que cada tarea:
    - Tiene una sesión de BD limpia
    - Cierra la sesión al finalizar
    - Hace rollback en caso de error
    """

    _db: Session | None = None
    _bot: Bot | None = None

    def after_return(self, status, retval, task_id, args, kwargs, einfo):
        """
        Hook ejecutado después de que la tarea retorna.

        Cierra la sesión de BD.
        """
        if self._db is not None:
            self._db.close()
            self._db = None

    @property
    def db(self) -> Session:
        """
        Lazy-load de sesión de BD.

        Returns:
            Session de SQLAlchemy.
        """
        if self._db is None:
            self._db = SessionLocal()
        return self._db

    @property
    def bot(self) -> Bot:
        """
        Lazy-load de instancia de Bot de Telegram.

        Returns:
            Bot instance configurado con el token.
        """
        if self._bot is None:
            self._bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)
        return self._bot


# ==================== EXCEPCIONES PERSONALIZADAS ====================


class SummaryNotFoundError(Exception):
    """El resumen no existe en la base de datos."""

    pass


class SummaryAlreadySentError(Exception):
    """El resumen ya fue enviado (idempotencia)."""

    pass


# ==================== TAREAS ====================


@celery_app.task(
    name="distribute_summary",
    base=DatabaseTask,
    bind=True,
    max_retries=3,
    default_retry_delay=60,  # 1 minuto entre reintentos
    autoretry_for=(TelegramError,),  # Retry automático para errores de Telegram
    retry_backoff=True,  # Exponential backoff
    retry_backoff_max=600,  # Max 10 minutos entre reintentos
    retry_jitter=True,  # Jitter aleatorio
    time_limit=300,  # 5 minutos max por tarea
)
def distribute_summary_task(self, summary_id_str: str) -> dict:
    """
    Tarea de Celery que distribuye un resumen a usuarios suscritos.

    Esta tarea:
    1. Obtiene el resumen de la BD con eager-loading de relaciones
    2. Valida que no haya sido enviado previamente (idempotencia)
    3. Consulta usuarios suscritos al source_id del video
    4. Envía mensaje formateado a cada usuario vía Telegram
    5. Maneja errores (usuario bloqueó bot, chat no existe, etc.)
    6. Actualiza summary.telegram_message_ids con IDs enviados
    7. Marca summary.sent_to_telegram = True

    Args:
        summary_id_str: UUID del resumen en formato string.

    Returns:
        dict con status, summary_id y cantidad de mensajes enviados.

    Raises:
        SummaryNotFoundError: Si el resumen no existe.
        SummaryAlreadySentError: Si el resumen ya fue enviado (idempotencia).

    Example:
        >>> task = distribute_summary_task.delay("123e4567-e89b-12d3-a456-426614174000")
        >>> task.id
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890'
        >>> task.status
        'PENDING'
    """
    summary_id = UUID(summary_id_str)

    # Usar context manager para logging estructurado con Request ID
    with task_context(
        task_name="distribute_summary",
        summary_id=summary_id_str,
        task_id=self.request.id,
        retries=self.request.retries,
    ):
        try:
            # Obtener resumen con eager-loading de relaciones
            summary_repo = SummaryRepository(self.db)
            summary = summary_repo.get_by_id(summary_id)

            if not summary:
                logger.error("summary_not_found")
                raise SummaryNotFoundError(f"Summary {summary_id} not found")

            # IDEMPOTENCIA: Si ya fue enviado, terminar inmediatamente
            if summary.sent_to_telegram:
                logger.bind(
                    sent_at=summary.sent_at.isoformat() if summary.sent_at else None,
                ).info("summary_already_sent")
                raise SummaryAlreadySentError(
                    f"Summary {summary_id} was already sent to Telegram"
                )

            # Obtener video y source relacionados (con eager loading)
            video = summary.transcription.video
            source = video.source

            logger.bind(
                video_id=str(video.id),
                source_id=str(source.id),
                source_name=source.name,
            ).info("summary_relations_fetched")

            # Consultar usuarios suscritos al source
            user_repo = TelegramUserRepository(self.db)
            subscribed_users = user_repo.get_users_subscribed_to_source(source.id)

            # Filtrar usuarios que NO bloquearon el bot
            active_users = [user for user in subscribed_users if not user.bot_blocked]

            logger.bind(
                total_subscribers=len(subscribed_users),
                active_users=len(active_users),
                blocked_users=len(subscribed_users) - len(active_users),
            ).info("users_count_calculated")

            # Si no hay usuarios activos, marcar como enviado y terminar
            if len(active_users) == 0:
                summary.sent_to_telegram = True
                summary.sent_at = datetime.now(timezone.utc)
                summary.telegram_message_ids = {}
                self.db.commit()

                logger.info("no_active_users_completing")

                return {
                    "status": "completed_no_users",
                    "summary_id": summary_id_str,
                    "messages_sent": 0,
                }

            # Formatear mensaje con markdown
            formatted_message = format_summary_message(summary, video, source)

            # Distribuir a usuarios (async)
            sent_message_ids = asyncio.run(
                _distribute_to_users(
                    bot=self.bot,
                    users=active_users,
                    message=formatted_message,
                    summary_id=summary_id_str,
                    user_repo=user_repo,
                    db_session=self.db,
                )
            )

            # Actualizar summary con IDs de mensajes enviados
            summary.telegram_message_ids = sent_message_ids
            summary.sent_to_telegram = True
            summary.sent_at = datetime.now(timezone.utc)
            self.db.commit()

            logger.bind(
                messages_sent=len(sent_message_ids),
                active_users=len(active_users),
            ).info("distribution_completed")

            return {
                "status": "completed",
                "summary_id": summary_id_str,
                "messages_sent": len(sent_message_ids),
                "active_users": len(active_users),
            }

        except (SummaryNotFoundError, SummaryAlreadySentError):
            # No reintentar estos errores (son permanentes o idempotentes)
            logger.error("permanent_error_occurred")
            raise

        except Exception as exc:
            # Log del error y permitir retry automático
            logger.bind(
                error=str(exc),
                error_type=type(exc).__name__,
            ).exception("distribution_error_occurred")
            # Celery hará retry automáticamente
            raise


# ==================== FUNCIONES AUXILIARES ====================


async def _distribute_to_users(
    bot: Bot,
    users: list,
    message: str,
    summary_id: str,
    user_repo: TelegramUserRepository,
    db_session: Session,
) -> dict[str, int]:
    """
    Distribuye el mensaje a todos los usuarios suscritos.

    Envía el mensaje a cada usuario y maneja errores individuales
    (usuario bloqueó bot, chat no existe, etc.). Respeta rate limits
    de Telegram (30 mensajes/segundo).

    Args:
        bot: Instancia de Bot de Telegram.
        users: Lista de TelegramUser suscritos.
        message: Mensaje formateado con markdown.
        summary_id: UUID del resumen (para logging).
        user_repo: Repositorio de usuarios (para marcar bot_blocked).
        db_session: Sesión de BD (para commits incrementales).

    Returns:
        dict: Mapeo de {chat_id: message_id} de mensajes enviados exitosamente.
    """
    sent_message_ids = {}
    RATE_LIMIT_DELAY = 0.05  # 50ms entre envíos (20 msg/s = seguro)

    for user in users:
        try:
            # Enviar mensaje con markdown v2
            sent_message = await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode="MarkdownV2",
                disable_web_page_preview=False,
            )

            # Guardar ID del mensaje enviado
            sent_message_ids[str(user.telegram_id)] = sent_message.message_id

            logger.bind(
                summary_id=summary_id,
                telegram_user_id=user.telegram_id,
                message_id=sent_message.message_id,
            ).debug("message_sent_to_user")

            # Rate limiting: esperar entre envíos
            await asyncio.sleep(RATE_LIMIT_DELAY)

        except Forbidden as e:
            # Usuario bloqueó el bot o chat no existe
            logger.bind(
                summary_id=summary_id,
                telegram_user_id=user.telegram_id,
                user_id=str(user.id),
                error=str(e),
            ).warning("user_blocked_bot")

            # Marcar usuario como bot_blocked en BD
            user.bot_blocked = True
            db_session.commit()

        except TelegramError as e:
            # Otros errores de Telegram (rate limit, timeout, etc.)
            logger.bind(
                summary_id=summary_id,
                telegram_user_id=user.telegram_id,
                user_id=str(user.id),
                error=str(e),
                error_type=type(e).__name__,
            ).error("telegram_send_failed")

            # Si es rate limit, propagar para retry
            if "too many requests" in str(e).lower():
                raise

            # Otros errores: continuar con siguiente usuario

        except Exception as e:
            # Error inesperado
            logger.bind(
                summary_id=summary_id,
                telegram_user_id=user.telegram_id,
                user_id=str(user.id),
                error=str(e),
            ).exception("unexpected_error_sending_message")
            # Continuar con siguiente usuario

    return sent_message_ids
