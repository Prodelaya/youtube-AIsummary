"""
Sistema de prompts para generación de resúmenes con LLMs.

Este módulo centraliza los prompts usados para resumir transcripciones,
permitiendo iteración y versionado sin modificar el código del servicio.
"""

from pathlib import Path

# Directorio donde están los archivos de prompts
PROMPTS_DIR = Path(__file__).parent


def load_prompt(filename: str) -> str:
    """
    Carga un prompt desde archivo.

    Args:
        filename: Nombre del archivo (ej: 'system_prompt.txt')

    Returns:
        Contenido del prompt como string.

    Raises:
        FileNotFoundError: Si el archivo no existe.
    """
    prompt_path = PROMPTS_DIR / filename
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt no encontrado: {prompt_path}")

    return prompt_path.read_text(encoding="utf-8").strip()


def format_user_prompt(title: str, duration: str, transcription: str) -> str:
    """
    Genera el prompt de usuario con los datos del vídeo.

    Args:
        title: Título del vídeo.
        duration: Duración formateada (ej: "15:30").
        transcription: Texto de la transcripción.

    Returns:
        Prompt de usuario formateado.
    """
    template = load_prompt("user_template.txt")
    return template.format(title=title, duration=duration, transcription=transcription)
