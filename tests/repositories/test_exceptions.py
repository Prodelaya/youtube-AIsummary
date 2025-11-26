"""
Tests unitarios para excepciones del Repository Pattern.

Valida el comportamiento de las excepciones personalizadas:
- RepositoryError (base)
- NotFoundError
- AlreadyExistsError
"""

from uuid import uuid4

import pytest

from src.repositories.exceptions import (
    AlreadyExistsError,
    NotFoundError,
    RepositoryError,
)


class TestRepositoryError:
    """Tests para la excepción base RepositoryError."""

    def test_repository_error_is_exception(self):
        """RepositoryError debe heredar de Exception."""
        error = RepositoryError("Error genérico")
        assert isinstance(error, Exception)
        assert str(error) == "Error genérico"

    def test_repository_error_without_message(self):
        """RepositoryError puede instanciarse sin mensaje."""
        error = RepositoryError()
        assert isinstance(error, Exception)

    def test_repository_error_can_be_raised(self):
        """RepositoryError puede ser lanzada y capturada."""
        with pytest.raises(RepositoryError) as exc_info:
            raise RepositoryError("Test error")
        assert str(exc_info.value) == "Test error"


class TestNotFoundError:
    """Tests para NotFoundError."""

    def test_not_found_error_message_with_uuid(self):
        """NotFoundError genera mensaje correcto con UUID."""
        resource_id = uuid4()
        error = NotFoundError("Source", resource_id)

        expected_message = f"Source con id '{resource_id}' no encontrado"
        assert str(error) == expected_message

    def test_not_found_error_message_with_string_id(self):
        """NotFoundError genera mensaje correcto con ID string."""
        error = NotFoundError("Video", "abc123")
        assert str(error) == "Video con id 'abc123' no encontrado"

    def test_not_found_error_message_with_int_id(self):
        """NotFoundError genera mensaje correcto con ID entero."""
        error = NotFoundError("User", 42)
        assert str(error) == "User con id '42' no encontrado"

    def test_not_found_error_attributes(self):
        """NotFoundError debe almacenar resource_type y resource_id."""
        resource_id = uuid4()
        error = NotFoundError("Source", resource_id)

        assert error.resource_type == "Source"
        assert error.resource_id == resource_id

    def test_not_found_error_inherits_from_repository_error(self):
        """NotFoundError debe heredar de RepositoryError."""
        error = NotFoundError("Source", uuid4())
        assert isinstance(error, RepositoryError)
        assert isinstance(error, Exception)

    def test_not_found_error_can_be_caught_specifically(self):
        """NotFoundError puede capturarse específicamente."""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError("Source", "test-id")

        assert exc_info.value.resource_type == "Source"
        assert exc_info.value.resource_id == "test-id"


class TestAlreadyExistsError:
    """Tests para AlreadyExistsError."""

    def test_already_exists_error_message(self):
        """AlreadyExistsError genera mensaje correcto."""
        error = AlreadyExistsError("Source", "url", "https://youtube.com/watch?v=xyz")
        expected_message = "Source con url='https://youtube.com/watch?v=xyz' ya existe"
        assert str(error) == expected_message

    def test_already_exists_error_message_with_int_value(self):
        """AlreadyExistsError genera mensaje correcto con valor entero."""
        error = AlreadyExistsError("User", "email_count", 5)
        assert str(error) == "User con email_count='5' ya existe"

    def test_already_exists_error_attributes(self):
        """AlreadyExistsError debe almacenar resource_type, field_name y field_value."""
        error = AlreadyExistsError("Source", "url", "https://example.com")

        assert error.resource_type == "Source"
        assert error.field_name == "url"
        assert error.field_value == "https://example.com"

    def test_already_exists_error_with_complex_value(self):
        """AlreadyExistsError puede almacenar valores complejos."""
        complex_value = {"key": "value", "nested": [1, 2, 3]}
        error = AlreadyExistsError("Config", "settings", complex_value)

        assert error.resource_type == "Config"
        assert error.field_name == "settings"
        assert error.field_value == complex_value

    def test_already_exists_error_inherits_from_repository_error(self):
        """AlreadyExistsError debe heredar de RepositoryError."""
        error = AlreadyExistsError("Source", "url", "https://example.com")
        assert isinstance(error, RepositoryError)
        assert isinstance(error, Exception)

    def test_already_exists_error_can_be_caught_specifically(self):
        """AlreadyExistsError puede capturarse específicamente."""
        with pytest.raises(AlreadyExistsError) as exc_info:
            raise AlreadyExistsError("Source", "url", "https://test.com")

        assert exc_info.value.resource_type == "Source"
        assert exc_info.value.field_name == "url"
        assert exc_info.value.field_value == "https://test.com"


class TestRepositoryErrorHierarchy:
    """Tests para validar la jerarquía de excepciones."""

    def test_can_catch_all_repository_errors_with_base_class(self):
        """Un except RepositoryError debe capturar todas las excepciones hijas."""
        caught_errors = []

        # Test NotFoundError
        try:
            raise NotFoundError("Source", uuid4())
        except RepositoryError as e:
            caught_errors.append(type(e).__name__)

        # Test AlreadyExistsError
        try:
            raise AlreadyExistsError("Source", "url", "https://example.com")
        except RepositoryError as e:
            caught_errors.append(type(e).__name__)

        # Test RepositoryError directa
        try:
            raise RepositoryError("Generic error")
        except RepositoryError as e:
            caught_errors.append(type(e).__name__)

        assert caught_errors == ["NotFoundError", "AlreadyExistsError", "RepositoryError"]

    def test_specific_catch_before_generic(self):
        """Captura específica debe tener prioridad sobre genérica."""
        caught_exception_type = None

        try:
            raise NotFoundError("Source", "test-id")
        except NotFoundError:
            caught_exception_type = "NotFoundError"
        except RepositoryError:
            caught_exception_type = "RepositoryError"

        assert caught_exception_type == "NotFoundError"

    def test_all_custom_exceptions_are_repository_errors(self):
        """Todas las excepciones custom deben ser instancias de RepositoryError."""
        exceptions = [
            NotFoundError("Test", "id"),
            AlreadyExistsError("Test", "field", "value"),
            RepositoryError("Test"),
        ]

        for exc in exceptions:
            assert isinstance(exc, RepositoryError)
            assert isinstance(exc, Exception)
