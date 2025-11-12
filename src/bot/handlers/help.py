"""
Handler del comando /help.

Muestra lista completa de comandos disponibles con descripciones.
"""

import logging

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Maneja el comando /help.

    Envía un mensaje con la lista de todos los comandos disponibles
    y sus descripciones, organizados por categorías.

    Args:
        update: Objeto de Telegram con info del mensaje
        context: Contexto del bot con datos de sesión

    Returns:
        None (envía mensaje directamente al usuario)
    """
    telegram_user = update.effective_user
    if telegram_user:
        logger.info(
            f"Comando /help solicitado por usuario {telegram_user.id} (@{telegram_user.username})",
            extra={"telegram_id": telegram_user.id, "username": telegram_user.username},
        )

    help_message = """📚 **COMANDOS DISPONIBLES**

**🚀 Inicio**
/start - Iniciar el bot y registrarse
/help - Mostrar esta ayuda

**📡 Suscripciones**
/sources - Ver y gestionar tus canales suscritos
_Elige qué canales de YouTube quieres seguir_

**📰 Consultar Resúmenes**
/recent - Ver los últimos 10 resúmenes de tus canales
/search `<palabra>` - Buscar resúmenes por keyword
_Ejemplo:_ `/search FastAPI`

**ℹ️ Información**
/stats - Ver estadísticas de uso (próximamente)
/about - Información del proyecto (próximamente)

**💡 Consejos de uso:**
1. Usa /sources para suscribirte a canales que te interesen
2. Recibirás resúmenes automáticamente cuando se publiquen nuevos videos
3. Usa /recent para ver los últimos resúmenes
4. Busca contenido antiguo con /search

**🔗 ¿Necesitas ayuda?**
Si encuentras algún problema, contacta al desarrollador: @prodelaya

---
_IA Monitor - Tu asistente personal de contenido sobre IA_
"""

    await update.message.reply_text(help_message, parse_mode="Markdown")
    logger.debug(f"Mensaje de ayuda enviado a usuario {telegram_user.id if telegram_user else 'desconocido'}")
