"""
OutputValidator: Validación de respuestas del LLM.

Valida que las respuestas de DeepSeek API cumplan con la estructura esperada
y no contengan filtraciones del system prompt o contenido inesperado.
"""

import json
import re
import structlog

logger = structlog.get_logger(__name__)


class OutputValidator:
    """
    Validador de salidas del LLM (DeepSeek API).

    Verifica que las respuestas del modelo cumplan con:
        - Estructura JSON correcta
        - Campos obligatorios presentes
        - No contienen system prompt leaked
        - Idioma correcto (español)
        - Longitud razonable
    """

    # Campos obligatorios en la respuesta del LLM
    REQUIRED_FIELDS = ["key_points", "topics", "full_summary"]

    # Patrones que indican prompt leakage
    PROMPT_LEAK_PATTERNS = [
        r"(system|assistant|user)\s*:\s*",
        r"you\s+are\s+an?\s+(assistant|ai|model)",
        r"your\s+(role|task|objective)\s+is\s+to",
        r"follow\s+these\s+instructions",
        r"<\|im_start\|>",  # DeepSeek/ChatML markers
        r"<\|im_end\|>",
    ]

    _compiled_leak_patterns = [
        re.compile(pattern, re.IGNORECASE) for pattern in PROMPT_LEAK_PATTERNS
    ]

    def validate_summary_structure(self, json_output: dict) -> bool:
        """
        Valida que la estructura JSON del resumen sea correcta.

        Args:
            json_output: Output del LLM parseado como dict.

        Returns:
            bool: True si la estructura es válida, False en caso contrario.

        Examples:
            >>> validator = OutputValidator()
            >>> valid_output = {
            ...     "key_points": ["punto 1", "punto 2"],
            ...     "topics": ["IA", "Python"],
            ...     "full_summary": "Resumen completo..."
            ... }
            >>> validator.validate_summary_structure(valid_output)
            True
        """
        if not isinstance(json_output, dict):
            logger.error("LLM output is not a dictionary")
            return False

        # Verificar campos obligatorios
        for field in self.REQUIRED_FIELDS:
            if field not in json_output:
                logger.error(f"Missing required field: {field}")
                return False

        # Validar tipos de datos
        if not isinstance(json_output.get("key_points"), list):
            logger.error("key_points must be a list")
            return False

        if not isinstance(json_output.get("topics"), list):
            logger.error("topics must be a list")
            return False

        if not isinstance(json_output.get("full_summary"), str):
            logger.error("full_summary must be a string")
            return False

        # Validar longitudes mínimas
        if len(json_output["key_points"]) == 0:
            logger.warning("key_points is empty")

        if len(json_output["topics"]) == 0:
            logger.warning("topics is empty")

        if len(json_output["full_summary"]) < 50:
            logger.warning("full_summary is too short", length=len(json_output["full_summary"]))

        return True

    def detect_prompt_leak(self, text: str) -> bool:
        """
        Detecta si el texto contiene filtraciones del system prompt.

        Args:
            text: Texto a analizar (full_summary u otros campos).

        Returns:
            bool: True si se detecta prompt leak, False en caso contrario.
        """
        for pattern in self._compiled_leak_patterns:
            if pattern.search(text):
                logger.warning("Prompt leak detected in LLM output", text_preview=text[:200])
                return True
        return False

    def validate_language(self, text: str) -> bool:
        """
        Valida que el texto esté mayormente en español (heurística).

        Args:
            text: Texto a validar.

        Returns:
            bool: True si parece ser español, False en caso contrario.

        Notes:
            - Heurística simple: busca palabras comunes en español
            - No es 100% preciso pero suficiente para detección básica
        """
        # Palabras comunes en español
        spanish_indicators = [
            r"\bel\b",
            r"\bla\b",
            r"\blos\b",
            r"\blas\b",
            r"\bde\b",
            r"\bdel\b",
            r"\ben\b",
            r"\bcon\b",
            r"\bque\b",
            r"\bpor\b",
            r"\bpara\b",
            r"\bun\b",
            r"\buna\b",
            r"\beste\b",
            r"\besta\b",
            r"\bestos\b",
            r"\bestas\b",
        ]

        spanish_matches = sum(
            1 for pattern in spanish_indicators if re.search(pattern, text, re.IGNORECASE)
        )

        # Si hay al menos 3 palabras comunes en español, consideramos que es español
        is_spanish = spanish_matches >= 3

        if not is_spanish:
            logger.warning(
                "Text might not be in Spanish",
                spanish_matches=spanish_matches,
                text_preview=text[:200],
            )

        return is_spanish

    def validate_length(self, text: str, min_length: int = 100, max_length: int = 5000) -> bool:
        """
        Valida que el texto tenga una longitud razonable.

        Args:
            text: Texto a validar.
            min_length: Longitud mínima aceptable.
            max_length: Longitud máxima aceptable.

        Returns:
            bool: True si la longitud es válida, False en caso contrario.
        """
        length = len(text)

        if length < min_length:
            logger.warning(f"Text too short: {length} < {min_length}")
            return False

        if length > max_length:
            logger.warning(f"Text too long: {length} > {max_length}")
            return False

        return True

    def validate_full_response(self, json_output: dict) -> tuple[bool, list[str]]:
        """
        Validación completa de la respuesta del LLM.

        Args:
            json_output: Output del LLM parseado como dict.

        Returns:
            tuple: (is_valid, list_of_errors)

        Examples:
            >>> validator = OutputValidator()
            >>> output = {"key_points": [], "topics": [], "full_summary": "Texto..."}
            >>> is_valid, errors = validator.validate_full_response(output)
            >>> if not is_valid:
            ...     print(f"Validation failed: {errors}")
        """
        errors = []

        # 1. Validar estructura
        if not self.validate_summary_structure(json_output):
            errors.append("Invalid structure")

        # 2. Validar prompt leak en full_summary
        full_summary = json_output.get("full_summary", "")
        if self.detect_prompt_leak(full_summary):
            errors.append("Prompt leak detected")

        # 3. Validar idioma
        if full_summary and not self.validate_language(full_summary):
            errors.append("Text might not be in Spanish")

        # 4. Validar longitud
        if full_summary and not self.validate_length(full_summary):
            errors.append("Invalid text length")

        is_valid = len(errors) == 0

        if not is_valid:
            logger.error("LLM output validation failed", errors=errors)

        return is_valid, errors
