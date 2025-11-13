"""
Handlers de comandos del bot de Telegram.

Cada handler es una función asíncrona que procesa un comando específico.
Todos los handlers reciben (update, context) como argumentos.
"""

from src.bot.handlers.help import help_handler
from src.bot.handlers.sources import sources_handler, toggle_subscription_callback
from src.bot.handlers.start import start_handler

__all__ = ["start_handler", "help_handler", "sources_handler", "toggle_subscription_callback"]
