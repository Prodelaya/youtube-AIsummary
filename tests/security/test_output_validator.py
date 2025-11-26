"""
Tests unitarios para OutputValidator.

Cobertura completa de:
    - validate_summary_structure()
    - detect_prompt_leak()
    - validate_language()
    - validate_length()
    - validate_full_response()
"""

import pytest

from src.services.output_validator import OutputValidator


class TestOutputValidator:
    """Test suite para OutputValidator."""

    @pytest.fixture
    def validator(self) -> OutputValidator:
        """Fixture: instancia de OutputValidator."""
        return OutputValidator()

    @pytest.fixture
    def valid_output(self) -> dict:
        """Fixture: output válido del LLM."""
        return {
            "key_points": [
                "Punto clave 1 sobre inteligencia artificial",
                "Punto clave 2 sobre machine learning",
                "Punto clave 3 sobre Python",
            ],
            "topics": ["IA", "Machine Learning", "Python", "FastAPI"],
            "full_summary": (
                "Este vídeo trata sobre inteligencia artificial y machine learning. "
                "Se explican los conceptos básicos de Python y FastAPI para el desarrollo "
                "de aplicaciones modernas. El contenido es muy útil para desarrolladores "
                "que quieren aprender sobre estas tecnologías. Se cubren temas como redes "
                "neuronales, algoritmos de clasificación y buenas prácticas de código."
            ),
        }


class TestValidateSummaryStructure(TestOutputValidator):
    """Tests para validate_summary_structure()."""

    def test_valid_structure(self, validator: OutputValidator, valid_output: dict):
        """Test: estructura válida con todos los campos."""
        result = validator.validate_summary_structure(valid_output)
        assert result is True

    def test_invalid_type_not_dict(self, validator: OutputValidator):
        """Test: input no es un diccionario."""
        result = validator.validate_summary_structure("not a dict")
        assert result is False

    def test_invalid_type_none(self, validator: OutputValidator):
        """Test: input es None."""
        result = validator.validate_summary_structure(None)
        assert result is False

    def test_missing_key_points(self, validator: OutputValidator):
        """Test: falta campo 'key_points'."""
        output = {"topics": ["IA"], "full_summary": "Resumen..."}
        result = validator.validate_summary_structure(output)
        assert result is False

    def test_missing_topics(self, validator: OutputValidator):
        """Test: falta campo 'topics'."""
        output = {"key_points": ["punto"], "full_summary": "Resumen..."}
        result = validator.validate_summary_structure(output)
        assert result is False

    def test_missing_full_summary(self, validator: OutputValidator):
        """Test: falta campo 'full_summary'."""
        output = {"key_points": ["punto"], "topics": ["IA"]}
        result = validator.validate_summary_structure(output)
        assert result is False

    def test_key_points_not_list(self, validator: OutputValidator):
        """Test: 'key_points' no es lista."""
        output = {
            "key_points": "not a list",
            "topics": ["IA"],
            "full_summary": "Resumen...",
        }
        result = validator.validate_summary_structure(output)
        assert result is False

    def test_topics_not_list(self, validator: OutputValidator):
        """Test: 'topics' no es lista."""
        output = {
            "key_points": ["punto"],
            "topics": "not a list",
            "full_summary": "Resumen...",
        }
        result = validator.validate_summary_structure(output)
        assert result is False

    def test_full_summary_not_string(self, validator: OutputValidator):
        """Test: 'full_summary' no es string."""
        output = {"key_points": ["punto"], "topics": ["IA"], "full_summary": 12345}
        result = validator.validate_summary_structure(output)
        assert result is False

    def test_empty_key_points(self, validator: OutputValidator):
        """Test: 'key_points' vacío (warning pero válido)."""
        output = {"key_points": [], "topics": ["IA"], "full_summary": "Resumen largo " * 10}
        result = validator.validate_summary_structure(output)
        assert result is True  # No falla, solo warning

    def test_empty_topics(self, validator: OutputValidator):
        """Test: 'topics' vacío (warning pero válido)."""
        output = {"key_points": ["punto"], "topics": [], "full_summary": "Resumen largo " * 10}
        result = validator.validate_summary_structure(output)
        assert result is True  # No falla, solo warning

    def test_short_full_summary(self, validator: OutputValidator):
        """Test: 'full_summary' muy corto (<50 chars, warning pero válido)."""
        output = {"key_points": ["punto"], "topics": ["IA"], "full_summary": "Corto"}
        result = validator.validate_summary_structure(output)
        assert result is True  # No falla, solo warning


class TestDetectPromptLeak(TestOutputValidator):
    """Tests para detect_prompt_leak()."""

    def test_no_prompt_leak(self, validator: OutputValidator):
        """Test: texto limpio sin prompt leak."""
        text = "Este es un resumen sobre inteligencia artificial y Python."
        result = validator.detect_prompt_leak(text)
        assert result is False

    def test_leak_system_marker(self, validator: OutputValidator):
        """Test: detección de 'system:'."""
        text = "system: You are an AI assistant..."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_assistant_marker(self, validator: OutputValidator):
        """Test: detección de 'assistant:'."""
        text = "assistant: Sure, I will help you..."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_user_marker(self, validator: OutputValidator):
        """Test: detección de 'user:'."""
        text = "user: Please summarize this video..."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_you_are_assistant(self, validator: OutputValidator):
        """Test: detección de 'you are an assistant'."""
        text = "You are an AI assistant that summarizes videos."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_your_role(self, validator: OutputValidator):
        """Test: detección de 'your role is to'."""
        text = "Your role is to analyze and summarize content."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_follow_instructions(self, validator: OutputValidator):
        """Test: detección de 'follow these instructions'."""
        text = "Follow these instructions to create a summary."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_deepseek_im_start(self, validator: OutputValidator):
        """Test: detección de marker DeepSeek '<|im_start|>'."""
        text = "Some text <|im_start|> system content..."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_deepseek_im_end(self, validator: OutputValidator):
        """Test: detección de marker DeepSeek '<|im_end|>'."""
        text = "Some text <|im_end|> more content..."
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_case_insensitive(self, validator: OutputValidator):
        """Test: detección case-insensitive."""
        text = "SYSTEM: This is a test"
        result = validator.detect_prompt_leak(text)
        assert result is True

    def test_leak_in_middle_of_text(self, validator: OutputValidator):
        """Test: detección de leak en medio del texto."""
        text = (
            "Este es un texto normal pero en medio aparece "
            "your task is to summarize y continúa el texto."
        )
        result = validator.detect_prompt_leak(text)
        assert result is True


class TestValidateLanguage(TestOutputValidator):
    """Tests para validate_language()."""

    def test_spanish_text(self, validator: OutputValidator):
        """Test: texto claramente en español."""
        text = (
            "Este vídeo trata sobre inteligencia artificial. "
            "El contenido es muy útil para los desarrolladores. "
            "Se explican conceptos de machine learning con ejemplos."
        )
        result = validator.validate_language(text)
        assert result is True

    def test_english_text(self, validator: OutputValidator):
        """Test: texto en inglés (debe fallar)."""
        text = (
            "This video talks about artificial intelligence. "
            "The content provides useful information about machine learning."
        )
        result = validator.validate_language(text)
        assert result is False

    def test_mixed_language_mostly_spanish(self, validator: OutputValidator):
        """Test: texto mixto con predominio español."""
        text = (
            "Este tutorial explica los conceptos de machine learning "
            "usando Python y TensorFlow para crear modelos predictivos."
        )
        result = validator.validate_language(text)
        assert result is True

    def test_minimal_spanish_indicators(self, validator: OutputValidator):
        """Test: texto con exactamente 3 indicadores españoles (umbral)."""
        text = "el modelo de machine learning con una arquitectura"
        result = validator.validate_language(text)
        assert result is True

    def test_below_spanish_threshold(self, validator: OutputValidator):
        """Test: texto con <3 indicadores españoles."""
        text = "artificial intelligence models"
        result = validator.validate_language(text)
        assert result is False

    def test_empty_string(self, validator: OutputValidator):
        """Test: string vacío."""
        result = validator.validate_language("")
        assert result is False

    def test_numbers_only(self, validator: OutputValidator):
        """Test: solo números."""
        result = validator.validate_language("123456789")
        assert result is False


class TestValidateLength(TestOutputValidator):
    """Tests para validate_length()."""

    def test_valid_length_default_range(self, validator: OutputValidator):
        """Test: longitud válida con rangos por defecto (100-5000)."""
        text = "a" * 500
        result = validator.validate_length(text)
        assert result is True

    def test_too_short_default(self, validator: OutputValidator):
        """Test: texto muy corto (<100 chars)."""
        text = "a" * 50
        result = validator.validate_length(text)
        assert result is False

    def test_too_long_default(self, validator: OutputValidator):
        """Test: texto muy largo (>5000 chars)."""
        text = "a" * 6000
        result = validator.validate_length(text)
        assert result is False

    def test_exact_min_length(self, validator: OutputValidator):
        """Test: longitud exacta al mínimo."""
        text = "a" * 100
        result = validator.validate_length(text)
        assert result is True

    def test_exact_max_length(self, validator: OutputValidator):
        """Test: longitud exacta al máximo."""
        text = "a" * 5000
        result = validator.validate_length(text)
        assert result is True

    def test_custom_range_valid(self, validator: OutputValidator):
        """Test: rango personalizado válido."""
        text = "a" * 75
        result = validator.validate_length(text, min_length=50, max_length=100)
        assert result is True

    def test_custom_range_too_short(self, validator: OutputValidator):
        """Test: rango personalizado, texto muy corto."""
        text = "a" * 25
        result = validator.validate_length(text, min_length=50, max_length=100)
        assert result is False

    def test_custom_range_too_long(self, validator: OutputValidator):
        """Test: rango personalizado, texto muy largo."""
        text = "a" * 150
        result = validator.validate_length(text, min_length=50, max_length=100)
        assert result is False

    def test_zero_length(self, validator: OutputValidator):
        """Test: string vacío (longitud 0)."""
        result = validator.validate_length("")
        assert result is False


class TestValidateFullResponse(TestOutputValidator):
    """Tests para validate_full_response()."""

    def test_fully_valid_response(self, validator: OutputValidator, valid_output: dict):
        """Test: respuesta completamente válida."""
        is_valid, errors = validator.validate_full_response(valid_output)
        assert is_valid is True
        assert len(errors) == 0

    def test_invalid_structure_only(self, validator: OutputValidator):
        """Test: solo estructura inválida."""
        output = {"key_points": "not a list"}  # Falta campos y tipo incorrecto
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is False
        assert "Invalid structure" in errors

    def test_prompt_leak_detected(self, validator: OutputValidator):
        """Test: detección de prompt leak."""
        output = {
            "key_points": ["punto 1", "punto 2"],
            "topics": ["IA"],
            "full_summary": (
                "Este es un resumen pero contiene system: instructions leaked "
                "que no deberían estar en la respuesta del modelo de lenguaje."
            ),
        }
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is False
        assert "Prompt leak detected" in errors

    def test_non_spanish_language(self, validator: OutputValidator):
        """Test: idioma no español."""
        output = {
            "key_points": ["point 1", "point 2"],
            "topics": ["AI"],
            "full_summary": (
                "This summary provides information about artificial intelligence "
                "and machine learning techniques for modern applications."
            ),
        }
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is False
        assert "Text might not be in Spanish" in errors

    def test_invalid_length(self, validator: OutputValidator):
        """Test: longitud inválida (muy corto)."""
        output = {
            "key_points": ["punto 1", "punto 2"],
            "topics": ["IA"],
            "full_summary": "Muy corto en español",
        }
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is False
        assert "Invalid text length" in errors

    def test_multiple_errors(self, validator: OutputValidator):
        """Test: múltiples errores simultáneos."""
        output = {
            "key_points": "not a list",  # Error estructura
            "topics": ["AI"],
            "full_summary": "Short system: leaked",  # Error length + prompt leak
        }
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is False
        assert len(errors) >= 2
        assert "Invalid structure" in errors
        assert "Prompt leak detected" in errors

    def test_missing_full_summary_field(self, validator: OutputValidator):
        """Test: campo full_summary faltante."""
        output = {"key_points": ["punto"], "topics": ["IA"]}
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is False
        assert "Invalid structure" in errors

    def test_empty_full_summary(self, validator: OutputValidator):
        """Test: full_summary vacío."""
        output = {"key_points": ["punto"], "topics": ["IA"], "full_summary": ""}
        is_valid, errors = validator.validate_full_response(output)
        # full_summary vacío es técnicamente válido (estructura OK, no valida idioma/longitud si está vacío)
        # Aunque validate_summary_structure genera warning, no falla
        assert is_valid is True
        assert len(errors) == 0

    def test_edge_case_exactly_100_chars_spanish(self, validator: OutputValidator):
        """Test: caso límite con exactamente 100 caracteres en español."""
        # Asegurar que sea exactamente 100 chars con palabras españolas
        summary = "Este texto sirve para validar el caso limite de exactamente cien caracteres en lengua espanola hoy y"
        assert len(summary) == 100

        output = {
            "key_points": ["punto 1", "punto 2"],
            "topics": ["IA", "Python"],
            "full_summary": summary,
        }
        is_valid, errors = validator.validate_full_response(output)
        # Debe pasar estructura, idioma y longitud
        assert is_valid is True
        assert len(errors) == 0

    def test_edge_case_exactly_5000_chars(self, validator: OutputValidator):
        """Test: caso límite con exactamente 5000 caracteres."""
        # Crear texto con palabras españolas repetidas
        base = "Este es un resumen sobre inteligencia artificial en Python. "
        summary = base * 84  # ~5040 chars, ajustar a 5000
        summary = summary[:5000]

        output = {
            "key_points": ["punto 1", "punto 2"],
            "topics": ["IA"],
            "full_summary": summary,
        }
        is_valid, errors = validator.validate_full_response(output)
        assert is_valid is True
        assert len(errors) == 0
