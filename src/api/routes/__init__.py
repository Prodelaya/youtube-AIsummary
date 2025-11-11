"""
Routers de FastAPI para la API REST.

Este modulo exporta todos los routers organizados por dominio.
"""

from src.api.routes import transcriptions, videos

__all__ = ["videos", "transcriptions"]
