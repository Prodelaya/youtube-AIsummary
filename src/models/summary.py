"""
Modelo Summary - Representa resúmenes generados por DeepSeek API.

Los resúmenes se generan a partir de transcripciones de Whisper.
Contienen el texto resumido, keywords extraídas, categorización y
metadata sobre el proceso de generación (tokens usados, tiempo, etc.).
"""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ARRAY, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import TimestampedUUIDBase

# Import solo para type checking (no causa import circular)
if TYPE_CHECKING:
    from src.models.transcription import Transcription


class Summary(TimestampedUUIDBase):
    """
    Resumen de contenido generado por DeepSeek API.

    Almacena el texto resumido de una transcripción, junto con keywords
    extraídas, categorización y metadata técnica sobre el proceso de
    generación (modelo usado, tokens consumidos, tiempo de procesamiento).

    Atributos:
        id: Clave primaria UUID (de TimestampedUUIDBase)
        transcription_id: Clave foránea a Transcription (relación 1:1)
        summary_text: Texto del resumen generado
        keywords: Lista de palabras clave extraídas del contenido
        category: Categoría del contenido ('framework', 'language', 'tool', 'concept')
        model_used: Nombre del modelo LLM usado ('deepseek-chat', etc.)
        tokens_used: Número total de tokens consumidos (input + output)
        input_tokens: Tokens de la transcripción enviada
        output_tokens: Tokens del resumen generado
        processing_time_ms: Tiempo de procesamiento en milisegundos
        extra_metadata: Metadata adicional en formato JSON (opcional)
        sent_to_telegram: Si el resumen fue enviado al bot de Telegram
        sent_at: Timestamp de cuándo se envió a Telegram
        telegram_message_ids: IDs de mensajes de Telegram (formato JSONB)
        created_at: Timestamp de creación (de TimestampedUUIDBase)
        updated_at: Timestamp última modificación (de TimestampedUUIDBase)
        transcription: Relación al modelo Transcription (uno-a-uno)

    Ejemplos:
        >>> summary = Summary(
        ...     transcription_id=transcription.id,
        ...     summary_text="Este video explica cómo usar FastAPI...",
        ...     keywords=["FastAPI", "Python", "API REST", "async"],
        ...     category="framework",
        ...     model_used="deepseek-chat",
        ...     tokens_used=850,
        ...     input_tokens=700,
        ...     output_tokens=150
        ... )
    """

    __tablename__ = "summaries"

    # ==================== COLUMNAS ====================

    transcription_id: Mapped[UUID] = mapped_column(
        ForeignKey("transcriptions.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,  # Relación 1:1 con Transcription
        comment="Clave foránea a la transcripción resumida",
    )

    summary_text: Mapped[str] = mapped_column(
        Text,  # Sin límite de longitud
        nullable=False,
        comment="Texto del resumen generado",
    )

    keywords: Mapped[list[str] | None] = mapped_column(
        ARRAY(String(100)),  # Array de strings, cada keyword máx 100 chars
        nullable=True,
        comment="Lista de palabras clave extraídas del contenido",
    )

    category: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Categoría del contenido ('framework', 'language', 'tool', 'concept')",
    )

    model_used: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="deepseek-chat",
        comment="Modelo LLM usado para generar el resumen",
    )

    tokens_used: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Número total de tokens consumidos (input + output)",
    )

    input_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Tokens de la transcripción enviada",
    )

    output_tokens: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Tokens del resumen generado",
    )

    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Tiempo de procesamiento en milisegundos",
    )

    extra_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Metadata adicional del proceso de generación (temperatura, etc.)",
    )

    # ==================== CAMPOS PARA BOT DE TELEGRAM ====================

    sent_to_telegram: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
        comment="Si el resumen ya fue enviado al bot de Telegram",
    )

    sent_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Timestamp de cuándo se envió a Telegram",
    )

    telegram_message_ids: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="IDs de mensajes de Telegram donde se envió (formato: {chat_id: message_id})",
    )

    # ==================== RELACIONES ====================

    # Uno-a-uno: Un resumen pertenece a una transcripción
    transcription: Mapped["Transcription"] = relationship(
        "Transcription",
        back_populates="summary",
        lazy="joined",  # Carga eager de la transcripción al consultar resumen
    )

    # ==================== ÍNDICES ====================
    __table_args__ = (
        Index("ix_summaries_transcription_id", "transcription_id"),
        Index("ix_summaries_category", "category"),
        Index("ix_summaries_sent_to_telegram", "sent_to_telegram"),
        # NOTE: Índices GIN y full-text search se crean en la migración
        # debido a sintaxis específica de PostgreSQL que Pylance no reconoce
    )

    # ==================== MÉTODOS ====================

    def __repr__(self) -> str:
        """Representación en string para debugging."""
        keywords_str = ", ".join(self.keywords[:3]) if self.keywords else "none"
        return (
            f"<Summary(id={self.id}, transcription_id={self.transcription_id}, "
            f"category='{self.category}', keywords=[{keywords_str}], "
            f"length={len(self.summary_text)} chars)>"
        )

    def to_dict(self) -> dict:
        """
        Convertir modelo a diccionario.

        Útil para serialización JSON en respuestas de API.

        Returns:
            dict: Representación en diccionario del resumen.
        """
        return {
            "id": str(self.id),
            "transcription_id": str(self.transcription_id),
            "summary_text": self.summary_text,
            "keywords": self.keywords or [],
            "category": self.category,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "processing_time_ms": self.processing_time_ms,
            "extra_metadata": self.extra_metadata or {},
            "sent_to_telegram": self.sent_to_telegram,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "telegram_message_ids": self.telegram_message_ids or {},
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @property
    def word_count(self) -> int:
        """Calcular número aproximado de palabras en el resumen."""
        return len(self.summary_text.split())

    @property
    def has_keywords(self) -> bool:
        """Verificar si el resumen tiene keywords extraídas."""
        return self.keywords is not None and len(self.keywords) > 0

    @property
    def compression_ratio(self) -> float | None:
        """
        Calcular ratio de compresión del resumen.

        Compara tokens de salida vs entrada. Un ratio de 0.2 significa
        que el resumen es un 20% del tamaño de la transcripción original.

        Returns:
            float: Ratio entre 0.0 y 1.0, o None si no hay datos de tokens.
        """
        if self.input_tokens is None or self.output_tokens is None:
            return None
        if self.input_tokens == 0:
            return None
        return self.output_tokens / self.input_tokens

    @property
    def estimated_cost_usd(self) -> float | None:
        """
        Estimar costo de la llamada a DeepSeek API.

        Basado en precios de DeepSeek:
        - Input: $0.28 / 1M tokens
        - Output: $1.10 / 1M tokens

        Returns:
            float: Costo estimado en USD, o None si no hay datos.
        """
        if self.input_tokens is None or self.output_tokens is None:
            return None

        # Precios DeepSeek (nov 2024)
        INPUT_COST_PER_1M = 0.28
        OUTPUT_COST_PER_1M = 1.10

        input_cost = (self.input_tokens / 1_000_000) * INPUT_COST_PER_1M
        output_cost = (self.output_tokens / 1_000_000) * OUTPUT_COST_PER_1M

        return input_cost + output_cost
