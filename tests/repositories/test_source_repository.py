"""
Tests de integración para SourceRepository.

Estos tests validan el comportamiento del SourceRepository
usando una base de datos real de PostgreSQL con transacciones
que se revierten automáticamente al finalizar cada test.
"""

from uuid import uuid4

import pytest

from src.models import Source
from src.repositories.exceptions import NotFoundError
from src.repositories.source_repository import SourceRepository


class TestSourceRepositoryInheritance:
    """Tests que validan la herencia de BaseRepository."""

    def test_create_source_inherited(self, db_session):
        """create() heredado de BaseRepository debe funcionar correctamente."""
        # Arrange
        repo = SourceRepository(db_session)
        source = Source(
            name="New Channel",
            url="https://youtube.com/@NewChannel",
            source_type="youtube",
            active=True,
        )

        # Act
        created = repo.create(source)

        # Assert
        assert created.id is not None
        assert created.name == "New Channel"
        assert created.url == "https://youtube.com/@NewChannel"
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_get_by_id_success_inherited(self, db_session, sample_source):
        """get_by_id() heredado debe retornar source existente."""
        # Arrange
        repo = SourceRepository(db_session)

        # Act
        found = repo.get_by_id(sample_source.id)

        # Assert
        assert found.id == sample_source.id
        assert found.name == sample_source.name
        assert found.url == sample_source.url

    def test_get_by_id_not_found_inherited(self, db_session):
        """get_by_id() debe lanzar NotFoundError cuando no existe."""
        # Arrange
        repo = SourceRepository(db_session)
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            repo.get_by_id(non_existent_id)

        assert exc_info.value.resource_type == "Source"
        assert exc_info.value.resource_id == non_existent_id

    def test_list_all_inherited(self, db_session, source_factory):
        """list_all() heredado debe listar todas las sources."""
        # Arrange
        repo = SourceRepository(db_session)
        source1 = source_factory(name="Channel 1", url="https://youtube.com/@ch1")
        source2 = source_factory(name="Channel 2", url="https://youtube.com/@ch2")
        source3 = source_factory(name="Channel 3", url="https://youtube.com/@ch3")

        # Act
        all_sources = repo.list_all()

        # Assert
        assert len(all_sources) >= 3  # Al menos los 3 que creamos
        source_ids = [s.id for s in all_sources]
        assert source1.id in source_ids
        assert source2.id in source_ids
        assert source3.id in source_ids

    def test_list_all_pagination_inherited(self, db_session, source_factory):
        """list_all() con paginación debe funcionar correctamente."""
        # Arrange
        repo = SourceRepository(db_session)
        # Crear 5 sources
        for i in range(5):
            source_factory(name=f"Channel {i}", url=f"https://youtube.com/@ch{i}")

        # Act
        page1 = repo.list_all(limit=2, offset=0)
        page2 = repo.list_all(limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].id != page2[0].id  # Diferentes páginas

    def test_update_source_inherited(self, db_session, sample_source):
        """update() heredado debe actualizar correctamente."""
        # Arrange
        repo = SourceRepository(db_session)
        original_name = sample_source.name

        # Act
        sample_source.name = "Updated Channel Name"
        updated = repo.update(sample_source)

        # Assert
        assert updated.name == "Updated Channel Name"
        assert updated.name != original_name
        assert updated.id == sample_source.id

    def test_delete_source_inherited(self, db_session, sample_source):
        """delete() heredado debe eliminar correctamente."""
        # Arrange
        repo = SourceRepository(db_session)
        source_id = sample_source.id

        # Act
        repo.delete(sample_source)

        # Assert - Verificar que ya no existe
        with pytest.raises(NotFoundError):
            repo.get_by_id(source_id)

    def test_exists_inherited(self, db_session, sample_source):
        """exists() heredado debe funcionar correctamente."""
        # Arrange
        repo = SourceRepository(db_session)

        # Act & Assert - Existe
        assert repo.exists(sample_source.id) is True

        # Act & Assert - No existe
        assert repo.exists(uuid4()) is False


class TestSourceRepositoryGetByUrl:
    """Tests para el método get_by_url()."""

    def test_get_by_url_finds_existing_source(self, db_session, sample_source):
        """get_by_url() debe encontrar source existente por URL."""
        # Arrange
        repo = SourceRepository(db_session)

        # Act
        found = repo.get_by_url(sample_source.url)

        # Assert
        assert found is not None
        assert found.id == sample_source.id
        assert found.url == sample_source.url
        assert found.name == sample_source.name

    def test_get_by_url_returns_none_when_not_found(self, db_session):
        """get_by_url() debe retornar None cuando no existe."""
        # Arrange
        repo = SourceRepository(db_session)
        non_existent_url = "https://youtube.com/@NonExistent"

        # Act
        result = repo.get_by_url(non_existent_url)

        # Assert
        assert result is None

    def test_get_by_url_exact_match(self, db_session, source_factory):
        """get_by_url() debe hacer match exacto (case-sensitive)."""
        # Arrange
        repo = SourceRepository(db_session)
        source = source_factory(name="Exact Match", url="https://youtube.com/@ExactMatch")

        # Act - Buscar con URL exacta
        found_exact = repo.get_by_url("https://youtube.com/@ExactMatch")
        # Buscar con URL diferente (mayúsculas/minúsculas)
        found_different = repo.get_by_url("https://youtube.com/@exactmatch")

        # Assert
        assert found_exact is not None
        assert found_exact.id == source.id
        # PostgreSQL es case-sensitive por defecto en Text
        assert found_different is None

    def test_get_by_url_with_multiple_sources(self, db_session, source_factory):
        """get_by_url() debe retornar solo la source correcta entre múltiples."""
        # Arrange
        repo = SourceRepository(db_session)
        source_factory(name="Channel 1", url="https://youtube.com/@ch1")
        source2 = source_factory(name="Channel 2", url="https://youtube.com/@ch2")
        source_factory(name="Channel 3", url="https://youtube.com/@ch3")

        # Act
        found = repo.get_by_url(source2.url)

        # Assert
        assert found is not None
        assert found.id == source2.id
        assert found.name == "Channel 2"


class TestSourceRepositoryGetActiveSources:
    """Tests para el método get_active_sources()."""

    def test_get_active_sources_returns_only_active(
        self, db_session, sample_source, inactive_source
    ):
        """get_active_sources() debe retornar solo sources con active=True."""
        # Arrange
        repo = SourceRepository(db_session)

        # Act
        active_sources = repo.get_active_sources()

        # Assert
        assert len(active_sources) >= 1
        source_ids = [s.id for s in active_sources]
        assert sample_source.id in source_ids  # Active=True
        assert inactive_source.id not in source_ids  # Active=False

        # Verificar que todos son active=True
        for source in active_sources:
            assert source.active is True

    def test_get_active_sources_empty_when_all_inactive(self, db_session, source_factory):
        """get_active_sources() debe retornar lista vacía si todas están inactivas."""
        # Arrange
        repo = SourceRepository(db_session)
        # Crear solo sources inactivas
        source_factory(name="Inactive 1", url="https://youtube.com/@in1", active=False)
        source_factory(name="Inactive 2", url="https://youtube.com/@in2", active=False)

        # Limpiar cualquier source activa previa de otros tests
        all_sources = repo.list_all()
        for source in all_sources:
            if source.active:
                source.active = False
                repo.update(source)

        # Act
        active_sources = repo.get_active_sources()

        # Assert
        assert active_sources == []

    def test_get_active_sources_with_mixed_sources(self, db_session, source_factory):
        """get_active_sources() debe filtrar correctamente entre activas/inactivas."""
        # Arrange
        repo = SourceRepository(db_session)
        active1 = source_factory(name="Active 1", url="https://youtube.com/@a1", active=True)
        active2 = source_factory(name="Active 2", url="https://youtube.com/@a2", active=True)
        inactive1 = source_factory(name="Inactive 1", url="https://youtube.com/@i1", active=False)
        inactive2 = source_factory(name="Inactive 2", url="https://youtube.com/@i2", active=False)

        # Act
        active_sources = repo.get_active_sources()

        # Assert
        active_ids = [s.id for s in active_sources]
        assert active1.id in active_ids
        assert active2.id in active_ids
        assert inactive1.id not in active_ids
        assert inactive2.id not in active_ids

    def test_get_active_sources_returns_list(self, db_session, sample_source):
        """get_active_sources() debe retornar siempre una lista."""
        # Arrange
        repo = SourceRepository(db_session)

        # Act
        result = repo.get_active_sources()

        # Assert
        assert isinstance(result, list)
        assert len(result) >= 1  # Al menos sample_source que es active=True


class TestSourceRepositoryExistsByUrl:
    """Tests para el método exists_by_url()."""

    def test_exists_by_url_returns_true_when_exists(self, db_session, sample_source):
        """exists_by_url() debe retornar True cuando la URL existe."""
        # Arrange
        repo = SourceRepository(db_session)

        # Act
        exists = repo.exists_by_url(sample_source.url)

        # Assert
        assert exists is True

    def test_exists_by_url_returns_false_when_not_exists(self, db_session):
        """exists_by_url() debe retornar False cuando la URL no existe."""
        # Arrange
        repo = SourceRepository(db_session)
        non_existent_url = "https://youtube.com/@NonExistent"

        # Act
        exists = repo.exists_by_url(non_existent_url)

        # Assert
        assert exists is False

    def test_exists_by_url_exact_match(self, db_session, source_factory):
        """exists_by_url() debe hacer match exacto (case-sensitive)."""
        # Arrange
        repo = SourceRepository(db_session)
        source_factory(name="Test", url="https://youtube.com/@ExactURL")

        # Act
        exists_exact = repo.exists_by_url("https://youtube.com/@ExactURL")
        exists_different_case = repo.exists_by_url("https://youtube.com/@exacturl")

        # Assert
        assert exists_exact is True
        assert exists_different_case is False

    def test_exists_by_url_with_multiple_sources(self, db_session, source_factory):
        """exists_by_url() debe funcionar correctamente con múltiples sources."""
        # Arrange
        repo = SourceRepository(db_session)
        source_factory(name="Channel 1", url="https://youtube.com/@ch1")
        source_factory(name="Channel 2", url="https://youtube.com/@ch2")
        source_factory(name="Channel 3", url="https://youtube.com/@ch3")

        # Act & Assert
        assert repo.exists_by_url("https://youtube.com/@ch1") is True
        assert repo.exists_by_url("https://youtube.com/@ch2") is True
        assert repo.exists_by_url("https://youtube.com/@ch3") is True
        assert repo.exists_by_url("https://youtube.com/@nonexistent") is False

    def test_exists_by_url_is_efficient(self, db_session, sample_source):
        """
        exists_by_url() debe ser eficiente (solo query de ID, no objeto completo).

        Este test es más conceptual - verifica que el método retorna bool.
        La eficiencia real se valida revisando el código (query solo de ID).
        """
        # Arrange
        repo = SourceRepository(db_session)

        # Act
        result = repo.exists_by_url(sample_source.url)

        # Assert
        assert isinstance(result, bool)
        assert result is True


class TestSourceRepositoryEdgeCases:
    """Tests de casos límite y validaciones."""

    def test_create_duplicate_url_raises_integrity_error(self, db_session, sample_source):
        """Intentar crear source con URL duplicada debe fallar (constraint UNIQUE)."""
        # Arrange
        repo = SourceRepository(db_session)
        duplicate_source = Source(
            name="Duplicate",
            url=sample_source.url,  # URL duplicada
            source_type="youtube",
        )

        # Act & Assert
        with pytest.raises(Exception):  # IntegrityError de SQLAlchemy
            repo.create(duplicate_source)

    def test_source_with_metadata(self, db_session):
        """Source puede crearse con metadata JSONB compleja."""
        # Arrange
        repo = SourceRepository(db_session)
        source = Source(
            name="Metadata Channel",
            url="https://youtube.com/@MetadataTest",
            source_type="youtube",
            active=True,
            extra_metadata={
                "subscriber_count": 500000,
                "language": "es",
                "topics": ["AI", "Programming", "Tech"],
                "verified": True,
            },
        )

        # Act
        created = repo.create(source)

        # Assert
        assert created.extra_metadata["subscriber_count"] == 500000
        assert created.extra_metadata["language"] == "es"
        assert "AI" in created.extra_metadata["topics"]

    def test_get_by_url_after_update(self, db_session, sample_source):
        """get_by_url() debe encontrar source después de actualizar su URL."""
        # Arrange
        repo = SourceRepository(db_session)
        new_url = "https://youtube.com/@UpdatedURL"

        # Act - Actualizar URL
        sample_source.url = new_url
        repo.update(sample_source)

        # Assert - Buscar por nueva URL
        found = repo.get_by_url(new_url)
        assert found is not None
        assert found.id == sample_source.id
        assert found.url == new_url
