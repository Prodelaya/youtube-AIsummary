"""
Tests unitarios para SourceRepository.

Estrategia de testing:
- Usar PostgreSQL en Docker (compatibilidad total con JSONB)
- Tests aislados con limpieza automática entre tests
- Validación de CRUD completo
- Validación de queries de filtrado
"""

from uuid import uuid4

import pytest

from src.models import Source
from src.repositories.exceptions import NotFoundError
from src.repositories.source_repository import SourceRepository


class TestSourceRepositoryCRUD:
    """Tests para operaciones CRUD básicas."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que crea una instancia del repository."""
        return SourceRepository(db_session)

    def test_create_source(self, repository, db_session):
        """Test 1: Crear fuente exitosamente"""
        # Arrange
        source = Source(
            name="New Channel",
            source_type="youtube",
            url="https://youtube.com/@newchannel",
            active=True,
        )

        # Act
        created = repository.create(source)
        db_session.commit()

        # Assert
        assert created.id is not None
        assert created.name == "New Channel"
        assert created.source_type == "youtube"
        assert created.url == "https://youtube.com/@newchannel"
        assert created.active is True

    def test_get_by_id_found(self, repository, sample_source):
        """Test 2: Obtener fuente por ID existente"""
        # Act
        source = repository.get_by_id(sample_source.id)

        # Assert
        assert source is not None
        assert source.id == sample_source.id
        assert source.name == sample_source.name
        assert source.url == sample_source.url

    def test_get_by_id_not_found(self, repository):
        """Test 3: Obtener fuente por ID inexistente lanza NotFoundError"""
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(non_existent_id)

    def test_list_all_sources(self, repository, multiple_sources):
        """Test 4: Listar todas las fuentes"""
        # Act
        sources = repository.list_all()

        # Assert
        assert len(sources) == 5
        assert all(isinstance(s, Source) for s in sources)

    def test_list_all_with_limit(self, repository, multiple_sources):
        """Test 5: Listar con límite"""
        # Act
        sources = repository.list_all(limit=2)

        # Assert
        assert len(sources) == 2

    def test_list_all_with_offset(self, repository, multiple_sources):
        """Test 6: Listar con offset"""
        # Act
        all_sources = repository.list_all()
        offset_sources = repository.list_all(offset=2)

        # Assert
        assert len(offset_sources) == 3
        # Los IDs deben ser diferentes (saltó los primeros 2)
        offset_ids = {s.id for s in offset_sources}
        first_two_ids = {s.id for s in all_sources[:2]}
        assert offset_ids.isdisjoint(first_two_ids)

    def test_update_source(self, repository, sample_source, db_session):
        """Test 7: Actualizar fuente exitosamente"""
        # Arrange
        original_name = sample_source.name
        sample_source.name = "Updated Channel Name"

        # Act
        updated = repository.update(sample_source)
        db_session.commit()

        # Assert
        assert updated.id == sample_source.id
        assert updated.name == "Updated Channel Name"
        assert updated.name != original_name

    def test_delete_source(self, repository, sample_source, db_session):
        """Test 8: Eliminar fuente exitosamente"""
        # Arrange
        source_id = sample_source.id

        # Act
        repository.delete(sample_source)
        db_session.commit()

        # Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(source_id)

    def test_exists_true(self, repository, sample_source):
        """Test 9: exists() retorna True para ID existente"""
        # Act
        result = repository.exists(sample_source.id)

        # Assert
        assert result is True

    def test_exists_false(self, repository):
        """Test 10: exists() retorna False para ID inexistente"""
        # Arrange
        non_existent_id = uuid4()

        # Act
        result = repository.exists(non_existent_id)

        # Assert
        assert result is False


class TestSourceRepositoryQueries:
    """Tests para queries especializadas."""

    @pytest.fixture
    def repository(self, db_session):
        return SourceRepository(db_session)

    def test_get_active_sources(self, repository, multiple_sources):
        """Test 11: Obtener solo fuentes activas"""
        # Act
        active_sources = repository.get_active_sources()

        # Assert
        assert len(active_sources) == 3  # 3 de 5 están activas (i % 3 != 0)
        assert all(s.active for s in active_sources)

    def test_get_active_sources_empty(self, repository, inactive_source):
        """Test 12: Cuando solo hay fuentes inactivas retorna lista vacía"""
        # Act
        active_sources = repository.get_active_sources()

        # Assert
        assert active_sources == []

    def test_get_by_url_found(self, repository, sample_source):
        """Test 13: Buscar fuente por URL existente"""
        # Act
        source = repository.get_by_url(sample_source.url)

        # Assert
        assert source is not None
        assert source.id == sample_source.id
        assert source.url == sample_source.url

    def test_get_by_url_not_found(self, repository):
        """Test 14: Buscar por URL inexistente retorna None"""
        # Act
        source = repository.get_by_url("https://youtube.com/@nonexistent")

        # Assert
        assert source is None

    def test_exists_by_url_true(self, repository, sample_source):
        """Test 15: exists_by_url() retorna True para URL existente"""
        # Act
        result = repository.exists_by_url(sample_source.url)

        # Assert
        assert result is True

    def test_exists_by_url_false(self, repository):
        """Test 16: exists_by_url() retorna False para URL inexistente"""
        # Act
        result = repository.exists_by_url("https://youtube.com/@nonexistent")

        # Assert
        assert result is False


class TestSourceRepositoryEdgeCases:
    """Tests para casos edge y validaciones."""

    @pytest.fixture
    def repository(self, db_session):
        return SourceRepository(db_session)

    def test_list_all_empty_database(self, repository):
        """Test 17: list_all() retorna lista vacía cuando no hay datos"""
        # Act
        sources = repository.list_all()

        # Assert
        assert sources == []

    def test_create_with_metadata(self, repository, db_session):
        """Test 18: Crear fuente con metadata JSON"""
        # Arrange
        source = Source(
            name="Channel with Metadata",
            source_type="youtube",
            url="https://youtube.com/@metadata",
            active=True,
            extra_metadata={"subscriber_count": 500000, "language": "es"},
        )

        # Act
        created = repository.create(source)
        db_session.commit()

        # Assert
        assert created.extra_metadata is not None
        assert created.extra_metadata["subscriber_count"] == 500000
        assert created.extra_metadata["language"] == "es"

    def test_update_metadata(self, repository, sample_source, db_session):
        """Test 19: Actualizar metadata de fuente"""
        # Arrange
        sample_source.extra_metadata = {"new_field": "new_value"}

        # Act
        updated = repository.update(sample_source)
        db_session.commit()
        db_session.refresh(updated)

        # Assert
        assert updated.extra_metadata is not None
        assert updated.extra_metadata["new_field"] == "new_value"

    def test_get_active_sources_respects_active_flag(self, repository, db_session):
        """Test 20: get_active_sources() solo retorna sources con active=True"""
        # Arrange - crear mix de activas e inactivas
        sources = [
            Source(
                name=f"S{i}",
                source_type="youtube",
                url=f"https://youtube.com/@s{i}",
                active=(i % 2 == 0),
            )
            for i in range(6)
        ]
        for s in sources:
            repository.create(s)
        db_session.commit()

        # Act
        active = repository.get_active_sources()

        # Assert
        assert len(active) == 3  # Solo las pares (0, 2, 4)
        assert all(s.active for s in active)
