"""
InputSanitizer: Protección contra Prompt Injection.

Implementa detección y neutralización de patrones de ataque de prompt injection
siguiendo las recomendaciones de OWASP LLM Top 10.

Referencias:
    - https://owasp.org/www-project-top-10-for-large-language-model-applications/
    - https://github.com/OWASP/www-project-top-10-for-large-language-model-applications
"""

import re
import structlog

logger = structlog.get_logger(__name__)


class InputSanitizer:
    """
    Sanitizador de entradas para prevenir prompt injection attacks.

    Detecta y neutraliza patrones maliciosos en inputs de usuario antes de
    enviarlos al LLM (DeepSeek API).

    Patrones detectados:
        - Instrucciones de ignorar contexto previo
        - Intentos de revelar system prompt
        - Comandos de ejecución de código
        - Inyección de roles (assistant, system)
        - Code blocks maliciosos (```python, ```bash, etc.)
        - Prompt leaking attempts
    """

    # Patrones de prompt injection (case-insensitive)
    INJECTION_PATTERNS = [
        # Ignorar instrucciones previas
        r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|context|rules?)",
        r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|context|rules?)",
        r"forget\s+(everything|all)\s+(you\s+)?(know|learned|were\s+told)",
        # Revelar system prompt
        r"(show|reveal|display|print|tell|give)\s+(me\s+)?(the\s+)?(your\s+)?(system|original|initial)\s+(prompt|instructions?|rules?)",
        r"what\s+(is|are)\s+your\s+(system|original|initial)\s+(prompt|instructions?)",
        # Comandos de ejecución
        r"(execute|run|eval)\s+(code|command|script|function)",
        # Inyección de roles
        r"(assistant|system|user)\s*:\s*.{0,50}",
        r"new\s+(instruction|prompt|rule)s?\s*:",
        r"(act|behave|pretend)\s+as\s+(if|a|an)\s+\w+",
        # Code blocks
        r"```(python|bash|sh|javascript|js|sql|php|ruby|go|rust|java)",
        # SQL Injection patterns (básico - para detectar SQL en transcripciones)
        r"(select|insert|update|delete)\s+.{0,30}\s+(from|into|where)\s+\w+",
        r"'\s*(or|and)\s*'1'\s*=\s*'1",
        # Prompt leaking
        r"repeat\s+(the\s+)?(above|previous|first)\s+(instructions?|prompt)",
        r"(output|print|show)\s+your\s+(instructions?|prompt|system\s+message)",
    ]

    # Patrones compilados (para performance)
    _compiled_patterns = [
        re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in INJECTION_PATTERNS
    ]

    def sanitize_title(self, title: str) -> str:
        """
        Sanitiza el título del video.

        Args:
            title: Título original del video.

        Returns:
            str: Título sanitizado (sin patrones maliciosos).

        Notes:
            - Titles son cortos, bajo riesgo de injection compleja
            - Se limita longitud a 500 caracteres
            - Se eliminan caracteres de control
        """
        if not title:
            return ""

        # Limitar longitud
        title = title[:500]

        # Eliminar caracteres de control
        title = re.sub(r"[\x00-\x1F\x7F]", "", title)

        # Detectar injection attempts (solo logging, no bloquear títulos)
        if self._contains_injection_attempt(title):
            logger.warning("Potential injection in title (not blocked)", title_preview=title[:100])

        return title

    def sanitize_transcription(self, transcription: str) -> str:
        """
        Sanitiza la transcripción del video.

        Args:
            transcription: Transcripción original (Whisper output).

        Returns:
            str: Transcripción sanitizada.

        Notes:
            - Alto riesgo de injection (texto largo, usuario no controla origen)
            - Detecta patrones maliciosos y los neutraliza
            - Logging estructurado de intentos detectados
        """
        if not transcription:
            return ""

        # Detectar injection attempt
        if self._contains_injection_attempt(transcription):
            logger.warning(
                "Prompt injection attempt detected in transcription",
                transcription_preview=transcription[:200],
                matched_patterns=self._get_matched_patterns(transcription),
            )

            # Neutralizar instrucciones maliciosas
            transcription = self._neutralize_instructions(transcription)

        return transcription

    def _contains_injection_attempt(self, text: str) -> bool:
        """
        Verifica si el texto contiene patrones de prompt injection.

        Args:
            text: Texto a analizar.

        Returns:
            bool: True si se detecta injection, False en caso contrario.
        """
        for pattern in self._compiled_patterns:
            if pattern.search(text):
                return True
        return False

    def _get_matched_patterns(self, text: str) -> list[str]:
        """
        Obtiene lista de patrones que coinciden con el texto.

        Args:
            text: Texto a analizar.

        Returns:
            list[str]: Lista de nombres de patrones detectados.
        """
        matched = []
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(text):
                matched.append(f"pattern_{i}: {self.INJECTION_PATTERNS[i][:50]}...")
        return matched

    def _neutralize_instructions(self, text: str) -> str:
        """
        Neutraliza instrucciones maliciosas reemplazándolas con texto seguro.

        Args:
            text: Texto con potenciales instrucciones maliciosas.

        Returns:
            str: Texto neutralizado.

        Notes:
            - No elimina texto, solo lo neutraliza para evitar pérdida de contexto
            - Reemplaza patrones maliciosos con versiones seguras
        """
        neutralized = text

        # Reemplazar code blocks con descripción
        neutralized = re.sub(
            r"```(\w+)", r"[code block removed - \1]", neutralized, flags=re.IGNORECASE
        )

        # Reemplazar instrucciones de ignorar contexto
        neutralized = re.sub(
            r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|context|rules?)(\s+and\s+.{0,100})?",
            "[potentially malicious instruction removed]",
            neutralized,
            flags=re.IGNORECASE,
        )

        # Reemplazar disregard instructions
        neutralized = re.sub(
            r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions?|prompts?|context|rules?)",
            "[potentially malicious instruction removed]",
            neutralized,
            flags=re.IGNORECASE,
        )

        # Reemplazar intentos de revelar system prompt
        neutralized = re.sub(
            r"(show|reveal|display|print|tell)\s+(me\s+)?(the\s+)?(your\s+)?(system|original|initial)\s+(prompt|instructions?|rules?)",
            "[system prompt request removed]",
            neutralized,
            flags=re.IGNORECASE,
        )

        # Reemplazar inyección de roles
        neutralized = re.sub(
            r"(assistant|system|user)\s*:\s*",
            "[role injection removed]: ",
            neutralized,
            flags=re.IGNORECASE,
        )

        return neutralized

    def get_sanitization_stats(self, original: str, sanitized: str) -> dict:
        """
        Obtiene estadísticas de sanitización para análisis.

        Args:
            original: Texto original.
            sanitized: Texto sanitizado.

        Returns:
            dict: Estadísticas de sanitización.
        """
        return {
            "original_length": len(original),
            "sanitized_length": len(sanitized),
            "characters_removed": len(original) - len(sanitized),
            "injection_detected": self._contains_injection_attempt(original),
            "patterns_matched": len(self._get_matched_patterns(original)),
        }
