"""
Utilidades de formateo de mensajes para el bot de Telegram.

Este módulo proporciona funciones reutilizables para formatear mensajes
de Telegram con markdown, emojis y estructura consistente.
"""

from src.models.source import Source
from src.models.summary import Summary
from src.models.video import Video


def format_duration(seconds: int) -> str:
    """
    Convertir segundos a formato legible (MM:SS o HH:MM:SS).

    Args:
        seconds: Duración en segundos.

    Returns:
        str: Duración formateada.

    Ejemplos:
        >>> format_duration(125)
        '2:05'
        >>> format_duration(3665)
        '1:01:05'
        >>> format_duration(45)
        '0:45'
    """
    if seconds < 0:
        return "0:00"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes}:{secs:02d}"


def truncate_text(text: str, max_length: int) -> str:
    """
    Truncar texto con elipsis si excede max_length.

    Intenta cortar en palabra completa para mantener legibilidad.

    Args:
        text: Texto a truncar.
        max_length: Longitud máxima permitida.

    Returns:
        str: Texto truncado con "..." si excede el límite.

    Ejemplos:
        >>> truncate_text("Hello world this is a test", 15)
        'Hello world...'
        >>> truncate_text("Short", 10)
        'Short'
    """
    if len(text) <= max_length:
        return text

    # Truncar en palabra completa
    truncated = text[: max_length - 3]
    last_space = truncated.rfind(" ")

    if last_space > 0:
        truncated = truncated[:last_space]

    return truncated + "..."


def format_summary_message(summary: Summary, video: Video, source: Source) -> str:
    """
    Formatear resumen como mensaje de Telegram con markdown.

    Genera un mensaje estructurado con:
    - Título del video (con link)
    - Información del canal
    - Duración
    - Tags (keywords)
    - Resumen del contenido

    Args:
        summary: Objeto Summary del ORM.
        video: Objeto Video relacionado.
        source: Objeto Source (canal) relacionado.

    Returns:
        str: Mensaje formateado con markdown de Telegram.

    Note:
        El mensaje final respeta el límite de 4096 caracteres de Telegram.
    """
    # Límite de Telegram: 4096 chars, dejamos margen para seguridad
    MAX_MESSAGE_LENGTH = 4000
    MAX_SUMMARY_LENGTH = 800

    # Header con título y link
    # Escapar caracteres especiales de Markdown v2 solo en el título
    safe_title = _escape_markdown_v2(video.title)
    message_parts = [
        f"📹 *Título:* [{safe_title}]({video.url})\n",
    ]

    # Información del canal
    safe_source_name = _escape_markdown_v2(source.name)
    message_parts.append(f"🎬 *Canal:* {safe_source_name}\n")

    # Duración
    if video.duration_seconds:
        duration_str = format_duration(video.duration_seconds)
        message_parts.append(f"⏱️ *Duración:* {duration_str}\n")

    # Tags (keywords)
    if summary.keywords and len(summary.keywords) > 0:
        # Limitar a 5 keywords más relevantes
        tags = ["#" + kw.replace(" ", "_") for kw in summary.keywords[:5]]
        message_parts.append(f"🏷️ *Tags:* {' '.join(tags)}\n")

    # Separador
    message_parts.append("\n📝 *Resumen:*\n")

    # Resumen del contenido (truncado)
    summary_text = truncate_text(summary.summary_text, MAX_SUMMARY_LENGTH)
    # Escapar el texto del resumen
    safe_summary = _escape_markdown_v2(summary_text)
    message_parts.append(f"{safe_summary}\n")

    # Metadata opcional (vistas, fecha de publicación)
    metadata_parts = []

    if video.extra_metadata and "view_count" in video.extra_metadata:
        view_count = video.extra_metadata["view_count"]
        formatted_views = _format_number(view_count)
        metadata_parts.append(f"👁️ {formatted_views} vistas")

    if video.published_at:
        # Formatear fecha en formato legible
        date_str = video.published_at.strftime("%d/%m/%Y")
        metadata_parts.append(f"📅 {date_str}")

    if metadata_parts:
        message_parts.append(f"\n📊 {' • '.join(metadata_parts)}")

    # Unir todas las partes
    full_message = "".join(message_parts)

    # Verificar longitud total y truncar si es necesario
    if len(full_message) > MAX_MESSAGE_LENGTH:
        # Truncar el resumen aún más si es necesario
        available_length = MAX_MESSAGE_LENGTH - (len(full_message) - len(safe_summary))
        summary_text = truncate_text(summary.summary_text, available_length - 10)
        safe_summary = _escape_markdown_v2(summary_text)

        # Reconstruir el mensaje con resumen truncado
        full_message = "".join(message_parts[:-2] + [f"{safe_summary}\n"] + message_parts[-1:])

    return full_message


def _escape_markdown_v2(text: str) -> str:
    """
    Escapar caracteres especiales para Markdown V2 de Telegram.

    Telegram MarkdownV2 requiere escapar: _ * [ ] ( ) ~ ` > # + - = | { } . !

    Args:
        text: Texto a escapar.

    Returns:
        str: Texto con caracteres especiales escapados.
    """
    special_chars = r"_*[]()~`>#+-=|{}.!"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def _format_number(num: int) -> str:
    """
    Formatear número con separadores de miles.

    Args:
        num: Número a formatear.

    Returns:
        str: Número formateado (ej: "1,234,567").

    Ejemplos:
        >>> _format_number(1234567)
        '1,234,567'
        >>> _format_number(1000)
        '1,000'
    """
    return f"{num:,}"
