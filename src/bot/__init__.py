"""
Bot de Telegram multi-usuario.

Este módulo gestiona la interacción con usuarios a través de Telegram,
permitiendo suscripciones personalizadas, consulta de histórico y búsqueda.

Estructura:
- telegram_bot.py: Configuración principal y arranque del bot
- handlers/: Manejadores de comandos (/start, /help, /sources, etc.)
"""

from src.bot.telegram_bot import start_bot

__all__ = ["start_bot"]
