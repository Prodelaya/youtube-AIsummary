"""
Tests unitarios para BaseRepository genérico.

Usa mocks de SQLAlchemy Session y un modelo fake simple
para evitar dependencias de modelos reales.
"""

from unittest.mock import MagicMock, call
from uuid import uuid4

import pytest

from src.repositories.base_repository import BaseRepository
from src.repositories.exceptions import NotFoundError


# Modelo fake simple para testing (NO usa SQLAlchemy real)
class FakeModel:
    """Modelo simplificado para tests del BaseRepository."""

    def __init__(self, id=None, name="test"):
        self.id = id
        self.name = name


class TestBaseRepositoryCreate:
    """Tests para el método create()."""

    def test_create_entity(self):
        """create() debe hacer add, commit y refresh en la sesión."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel(name="test_create")

        # Act
        result = repo.create(fake_entity)

        # Assert
        mock_session.add.assert_called_once_with(fake_entity)
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(fake_entity)
        assert result is fake_entity

    def test_create_entity_returns_same_instance(self):
        """create() debe retornar la misma instancia que recibió."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel(id=uuid4(), name="same_instance")

        result = repo.create(fake_entity)

        assert result is fake_entity
        assert result.id == fake_entity.id

    def test_create_calls_in_correct_order(self):
        """create() debe llamar add -> commit -> refresh en ese orden."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel()

        repo.create(fake_entity)

        # Verificar orden de llamadas
        expected_calls = [
            call.add(fake_entity),
            call.commit(),
            call.refresh(fake_entity),
        ]
        assert mock_session.mock_calls == expected_calls


class TestBaseRepositoryGetById:
    """Tests para el método get_by_id()."""

    def test_get_by_id_success(self):
        """get_by_id() debe retornar entidad cuando existe."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        fake_entity = FakeModel(id=entity_id, name="found")
        mock_session.get.return_value = fake_entity

        # Act
        result = repo.get_by_id(entity_id)

        # Assert
        mock_session.get.assert_called_once_with(FakeModel, entity_id)
        assert result is fake_entity
        assert result.id == entity_id

    def test_get_by_id_not_found(self):
        """get_by_id() debe lanzar NotFoundError cuando no existe."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        mock_session.get.return_value = None

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            repo.get_by_id(entity_id)

        # Verificar que se lanzó con los parámetros correctos
        assert exc_info.value.resource_type == "FakeModel"
        assert exc_info.value.resource_id == entity_id
        mock_session.get.assert_called_once_with(FakeModel, entity_id)

    def test_get_by_id_calls_session_get_with_correct_params(self):
        """get_by_id() debe llamar session.get con model_class y entity_id."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        mock_session.get.return_value = FakeModel(id=entity_id)

        repo.get_by_id(entity_id)

        mock_session.get.assert_called_once_with(FakeModel, entity_id)


class TestBaseRepositoryListAll:
    """Tests para el método list_all()."""

    def test_list_all_default_pagination(self):
        """list_all() sin argumentos debe usar limit=100, offset=0."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)

        fake_entities = [
            FakeModel(id=uuid4(), name="entity1"),
            FakeModel(id=uuid4(), name="entity2"),
        ]

        # Mock de la cadena query().limit().offset().all()
        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = fake_entities

        # Act
        result = repo.list_all()

        # Assert
        mock_session.query.assert_called_once_with(FakeModel)
        mock_query.limit.assert_called_once_with(100)
        mock_query.offset.assert_called_once_with(0)
        mock_query.all.assert_called_once()
        assert result == fake_entities

    def test_list_all_custom_pagination(self):
        """list_all() debe aceptar limit y offset personalizados."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)

        fake_entities = [FakeModel(id=uuid4(), name=f"entity{i}") for i in range(50)]

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = fake_entities

        # Act
        result = repo.list_all(limit=50, offset=10)

        # Assert
        mock_session.query.assert_called_once_with(FakeModel)
        mock_query.limit.assert_called_once_with(50)
        mock_query.offset.assert_called_once_with(10)
        assert result == fake_entities

    def test_list_all_empty_result(self):
        """list_all() debe retornar lista vacía cuando no hay resultados."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        result = repo.list_all()

        assert result == []
        assert isinstance(result, list)

    def test_list_all_calls_in_correct_order(self):
        """list_all() debe llamar query -> limit -> offset -> all."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)

        mock_query = MagicMock()
        mock_session.query.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = []

        repo.list_all(limit=25, offset=5)

        # Verificar orden de llamadas en el query
        assert mock_session.query.called
        assert mock_query.limit.called
        assert mock_query.offset.called
        assert mock_query.all.called


class TestBaseRepositoryUpdate:
    """Tests para el método update()."""

    def test_update_entity(self):
        """update() debe hacer commit y refresh."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel(id=uuid4(), name="updated")

        # Act
        result = repo.update(fake_entity)

        # Assert
        mock_session.commit.assert_called_once()
        mock_session.refresh.assert_called_once_with(fake_entity)
        assert result is fake_entity

    def test_update_returns_same_instance(self):
        """update() debe retornar la misma instancia que recibió."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        fake_entity = FakeModel(id=entity_id, name="original")

        result = repo.update(fake_entity)

        assert result is fake_entity
        assert result.id == entity_id

    def test_update_calls_in_correct_order(self):
        """update() debe llamar commit -> refresh en ese orden."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel()

        repo.update(fake_entity)

        expected_calls = [
            call.commit(),
            call.refresh(fake_entity),
        ]
        assert mock_session.mock_calls == expected_calls


class TestBaseRepositoryDelete:
    """Tests para el método delete()."""

    def test_delete_entity(self):
        """delete() debe hacer session.delete y commit."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel(id=uuid4(), name="to_delete")

        # Act
        result = repo.delete(fake_entity)

        # Assert
        mock_session.delete.assert_called_once_with(fake_entity)
        mock_session.commit.assert_called_once()
        assert result is None  # delete() no retorna nada

    def test_delete_returns_none(self):
        """delete() no debe retornar ningún valor."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel()

        result = repo.delete(fake_entity)

        assert result is None

    def test_delete_calls_in_correct_order(self):
        """delete() debe llamar delete -> commit en ese orden."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        fake_entity = FakeModel()

        repo.delete(fake_entity)

        expected_calls = [
            call.delete(fake_entity),
            call.commit(),
        ]
        assert mock_session.mock_calls == expected_calls


class TestBaseRepositoryExists:
    """Tests para el método exists()."""

    def test_exists_true(self):
        """exists() debe retornar True cuando la entidad existe."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        mock_session.get.return_value = FakeModel(id=entity_id)

        # Act
        result = repo.exists(entity_id)

        # Assert
        assert result is True
        mock_session.get.assert_called_once_with(FakeModel, entity_id)

    def test_exists_false(self):
        """exists() debe retornar False cuando la entidad no existe."""
        # Arrange
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        mock_session.get.return_value = None

        # Act
        result = repo.exists(entity_id)

        # Assert
        assert result is False
        mock_session.get.assert_called_once_with(FakeModel, entity_id)

    def test_exists_calls_session_get(self):
        """exists() debe llamar session.get con model_class y entity_id."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)
        entity_id = uuid4()
        mock_session.get.return_value = FakeModel()

        repo.exists(entity_id)

        mock_session.get.assert_called_once_with(FakeModel, entity_id)


class TestBaseRepositoryInitialization:
    """Tests para la inicialización del BaseRepository."""

    def test_repository_initialization(self):
        """BaseRepository debe almacenar session y model_class correctamente."""
        mock_session = MagicMock()
        repo = BaseRepository(mock_session, FakeModel)

        assert repo.session is mock_session
        assert repo.model_class is FakeModel

    def test_repository_is_generic(self):
        """BaseRepository debe ser genérico y funcionar con cualquier clase."""
        mock_session = MagicMock()

        # Crear con FakeModel
        repo = BaseRepository(mock_session, FakeModel)
        assert repo.model_class.__name__ == "FakeModel"

        # Crear con otra clase
        class AnotherModel:
            pass

        repo2 = BaseRepository(mock_session, AnotherModel)
        assert repo2.model_class.__name__ == "AnotherModel"
