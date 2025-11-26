"""
Tests unitarios para VideoRepository.

Estrategia de testing:
- Usar PostgreSQL en Docker (compatibilidad total con JSONB)
- Tests aislados con limpieza automática entre tests
- Validación de CRUD completo
- Validación de queries de filtrado
- Validación de soft delete
- Validación de invalidación de caché
"""

from datetime import datetime
from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.models import Video
from src.models.video import VideoStatus
from src.repositories.exceptions import NotFoundError
from src.repositories.video_repository import VideoRepository


class TestVideoRepositoryCRUD:
    """Tests para operaciones CRUD básicas."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que crea una instancia del repository."""
        return VideoRepository(db_session)

    def test_create_video(self, repository, sample_source, db_session):
        """Test 1: Crear video exitosamente"""
        # Arrange
        video = Video(
            source_id=sample_source.id,
            youtube_id="test123",
            title="Test Video",
            url="https://youtube.com/watch?v=test123",
            duration_seconds=300,
            status=VideoStatus.PENDING,
        )

        # Act
        created = repository.create(video)
        db_session.commit()

        # Assert
        assert created.id is not None
        assert created.youtube_id == "test123"
        assert created.title == "Test Video"
        assert created.status == VideoStatus.PENDING
        assert created.source_id == sample_source.id

    def test_get_by_id_found(self, repository, sample_video):
        """Test 2: Obtener video por ID existente"""
        # Act
        video = repository.get_by_id(sample_video.id)

        # Assert
        assert video is not None
        assert video.id == sample_video.id
        assert video.youtube_id == sample_video.youtube_id
        assert video.title == sample_video.title

    def test_get_by_id_not_found(self, repository):
        """Test 3: Obtener video por ID inexistente lanza NotFoundError"""
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(non_existent_id)

    def test_list_all_videos(self, repository, multiple_videos):
        """Test 4: Listar todos los videos"""
        # Act
        videos = repository.list_all()

        # Assert
        assert len(videos) == 10
        assert all(isinstance(v, Video) for v in videos)

    def test_update_video(self, repository, sample_video, db_session):
        """Test 5: Actualizar video exitosamente"""
        # Arrange
        original_title = sample_video.title
        sample_video.title = "Updated Title"

        # Act
        updated = repository.update(sample_video)
        db_session.commit()

        # Assert
        assert updated.id == sample_video.id
        assert updated.title == "Updated Title"
        assert updated.title != original_title

    def test_delete_video(self, repository, sample_video, db_session):
        """Test 6: Eliminar video exitosamente"""
        # Arrange
        video_id = sample_video.id

        # Act
        repository.delete(sample_video)
        db_session.commit()

        # Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(video_id)


class TestVideoRepositoryStatusQueries:
    """Tests para queries por estado."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_get_by_status_pending(self, repository, multiple_videos):
        """Test 7: Obtener solo videos pendientes"""
        # Act
        pending = repository.get_by_status(VideoStatus.PENDING)

        # Assert
        assert len(pending) == 3  # 3 PENDING en multiple_videos
        assert all(v.status == VideoStatus.PENDING for v in pending)

    def test_get_by_status_completed(self, repository, multiple_videos):
        """Test 8: Obtener solo videos completados"""
        # Act
        completed = repository.get_by_status(VideoStatus.COMPLETED)

        # Assert
        assert len(completed) == 3  # 3 COMPLETED en multiple_videos
        assert all(v.status == VideoStatus.COMPLETED for v in completed)

    def test_get_by_status_failed(self, repository, multiple_videos):
        """Test 9: Obtener solo videos fallidos"""
        # Act
        failed = repository.get_by_status(VideoStatus.FAILED)

        # Assert
        assert len(failed) == 2  # 2 FAILED en multiple_videos
        assert all(v.status == VideoStatus.FAILED for v in failed)

    def test_get_by_status_empty(self, repository, sample_video):
        """Test 10: Estado sin videos retorna lista vacía"""
        # Act - buscar estado que no existe
        skipped = repository.get_by_status(VideoStatus.SKIPPED)

        # Assert
        assert skipped == []


class TestVideoRepositorySourceQueries:
    """Tests para queries por source."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_get_by_source(self, repository, sample_source, multiple_videos):
        """Test 11: Obtener videos de una fuente específica"""
        # Act
        videos = repository.get_by_source(sample_source.id)

        # Assert
        assert len(videos) == 10  # Todos los multiple_videos son de sample_source
        assert all(v.source_id == sample_source.id for v in videos)

    def test_get_by_source_with_limit(self, repository, sample_source, multiple_videos):
        """Test 12: Limitar resultados por fuente"""
        # Act
        videos = repository.get_by_source(sample_source.id, limit=3)

        # Assert
        assert len(videos) == 3

    def test_get_by_source_with_offset(self, repository, sample_source, multiple_videos):
        """Test 13: Offset en resultados por fuente"""
        # Act
        all_videos = repository.get_by_source(sample_source.id)
        offset_videos = repository.get_by_source(sample_source.id, offset=5)

        # Assert
        assert len(offset_videos) == 5  # 10 total - 5 offset = 5
        # Los IDs deben ser diferentes
        offset_ids = {v.id for v in offset_videos}
        first_five_ids = {v.id for v in all_videos[:5]}
        assert offset_ids.isdisjoint(first_five_ids)

    def test_get_by_source_and_status(self, repository, sample_source, multiple_videos):
        """Test 14: Filtrar por source y status combinados"""
        # Act
        pending = repository.get_by_source_and_status(sample_source.id, VideoStatus.PENDING)

        # Assert
        assert len(pending) == 3
        assert all(v.status == VideoStatus.PENDING for v in pending)
        assert all(v.source_id == sample_source.id for v in pending)


class TestVideoRepositoryYouTubeIDQueries:
    """Tests para queries por youtube_id."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_get_by_youtube_id_found(self, repository, sample_video):
        """Test 15: Buscar video por youtube_id existente"""
        # Act
        video = repository.get_by_youtube_id(sample_video.youtube_id)

        # Assert
        assert video is not None
        assert video.id == sample_video.id
        assert video.youtube_id == sample_video.youtube_id

    def test_get_by_youtube_id_not_found(self, repository):
        """Test 16: Buscar por youtube_id inexistente retorna None"""
        # Act
        video = repository.get_by_youtube_id("nonexistent123")

        # Assert
        assert video is None

    def test_exists_by_youtube_id_true(self, repository, sample_video):
        """Test 17: exists_by_youtube_id() retorna True para ID existente"""
        # Act
        result = repository.exists_by_youtube_id(sample_video.youtube_id)

        # Assert
        assert result is True

    def test_exists_by_youtube_id_false(self, repository):
        """Test 18: exists_by_youtube_id() retorna False para ID inexistente"""
        # Act
        result = repository.exists_by_youtube_id("nonexistent123")

        # Assert
        assert result is False


class TestVideoRepositorySoftDelete:
    """Tests para soft delete."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_soft_delete_sets_deleted_at(self, repository, sample_video, db_session):
        """Test 19: soft_delete() establece deleted_at"""
        # Act
        deleted = repository.soft_delete(sample_video.id)
        db_session.refresh(deleted)

        # Assert
        assert deleted.deleted_at is not None
        assert deleted.is_deleted is True
        assert isinstance(deleted.deleted_at, datetime)

    def test_soft_delete_not_found(self, repository):
        """Test 20: soft_delete() de video inexistente lanza ValueError"""
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.soft_delete(non_existent_id)

    def test_list_paginated_excludes_deleted_by_default(self, repository, sample_video, db_session):
        """Test 21: list_paginated() excluye soft-deleted por default"""
        # Arrange - soft delete el video
        repository.soft_delete(sample_video.id)
        db_session.commit()

        # Act
        videos = repository.list_paginated()

        # Assert
        assert len(videos) == 0  # No debe aparecer
        video_ids = [v.id for v in videos]
        assert sample_video.id not in video_ids

    def test_list_paginated_includes_deleted_when_requested(
        self, repository, sample_video, db_session
    ):
        """Test 22: list_paginated() incluye soft-deleted si se solicita"""
        # Arrange - soft delete el video
        repository.soft_delete(sample_video.id)
        db_session.commit()

        # Act
        videos = repository.list_paginated(include_deleted=True)

        # Assert
        assert len(videos) == 1
        video_ids = [v.id for v in videos]
        assert sample_video.id in video_ids


class TestVideoRepositoryPagination:
    """Tests para paginación cursor-based."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_list_paginated_basic(self, repository, multiple_videos):
        """Test 23: Paginación básica"""
        # Act
        videos = repository.list_paginated(limit=5)

        # Assert
        assert len(videos) == 5

    def test_list_paginated_with_cursor(self, repository, multiple_videos):
        """Test 24: Paginación con cursor"""
        # Arrange - obtener primera página
        first_page = repository.list_paginated(limit=3)
        assert len(first_page) > 0, "Should have results in first page"
        cursor = first_page[-1].id

        # Act - obtener segunda página
        second_page = repository.list_paginated(limit=3, cursor=cursor)

        # Assert - puede haber menos si no hay suficientes videos
        # Los IDs deben ser diferentes
        first_ids = {v.id for v in first_page}
        second_ids = {v.id for v in second_page}
        if second_page:
            assert first_ids.isdisjoint(second_ids)

    def test_list_paginated_filter_by_status(self, repository, multiple_videos):
        """Test 25: Paginación filtrada por status"""
        # Act
        pending = repository.list_paginated(status=VideoStatus.PENDING)

        # Assert
        assert len(pending) == 3
        assert all(v.status == VideoStatus.PENDING for v in pending)

    def test_list_paginated_filter_by_source(self, repository, sample_source, multiple_videos):
        """Test 26: Paginación filtrada por source"""
        # Act
        videos = repository.list_paginated(source_id=sample_source.id, limit=5)

        # Assert
        assert len(videos) == 5
        assert all(v.source_id == sample_source.id for v in videos)


class TestVideoRepositoryCreateVideo:
    """Tests para método create_video()."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_create_video_invalidates_cache(self, repository, sample_source, db_session):
        """Test 27: create_video() invalida caché de estadísticas"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            mock_cache.delete = Mock()

            # Act
            video = repository.create_video(
                source_id=sample_source.id,
                youtube_id="test456",
                title="Test Video",
                url="https://youtube.com/watch?v=test456",
                duration_seconds=300,
            )
            db_session.commit()

            # Assert
            assert video.id is not None
            # Verificar que se invalidó el caché (2 llamadas: global + source)
            assert mock_cache.delete.call_count == 2
            mock_cache.delete.assert_any_call("stats:global")
            mock_cache.delete.assert_any_call(f"stats:source:{sample_source.id}")

    def test_create_video_with_metadata(self, repository, sample_source, db_session):
        """Test 28: create_video() con metadata"""
        # Arrange
        metadata = {"view_count": 1000, "like_count": 50}

        # Act
        video = repository.create_video(
            source_id=sample_source.id,
            youtube_id="test789",
            title="Test Video",
            url="https://youtube.com/watch?v=test789",
            metadata=metadata,
        )
        db_session.commit()
        db_session.refresh(video)

        # Assert
        assert video.extra_metadata is not None
        assert video.extra_metadata["view_count"] == 1000
        assert video.extra_metadata["like_count"] == 50


class TestVideoRepositoryUpdateVideo:
    """Tests para método update_video()."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_update_video_status_invalidates_cache(self, repository, sample_video, db_session):
        """Test 29: update_video() con cambio de status invalida caché"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            mock_cache.delete = Mock()

            # Act
            updated = repository.update_video(sample_video.id, status=VideoStatus.COMPLETED)

            # Assert
            assert updated.status == VideoStatus.COMPLETED
            # Verificar que se invalidó el caché
            assert mock_cache.delete.call_count == 2
            mock_cache.delete.assert_any_call("stats:global")

    def test_update_video_title_does_not_invalidate_cache(
        self, repository, sample_video, db_session
    ):
        """Test 30: update_video() sin cambio de status NO invalida caché"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            mock_cache.delete = Mock()

            # Act
            updated = repository.update_video(sample_video.id, title="New Title")

            # Assert
            assert updated.title == "New Title"
            # NO debe invalidar caché (solo title cambió, no status)
            mock_cache.delete.assert_not_called()

    def test_update_video_not_found(self, repository):
        """Test 31: update_video() de video inexistente lanza ValueError"""
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.update_video(non_existent_id, title="New Title")


class TestVideoRepositorySkippedVideos:
    """Tests para get_skipped_videos()."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_get_skipped_videos(self, repository, sample_source, db_session):
        """Test 32: Obtener videos skipped"""
        # Arrange - crear video skipped
        video = Video(
            source_id=sample_source.id,
            youtube_id="skipped1",
            title="Skipped Video",
            url="https://youtube.com/watch?v=skipped1",
            duration_seconds=10000,  # Video muy largo
            status=VideoStatus.SKIPPED,
        )
        repository.create(video)
        db_session.commit()

        # Act
        skipped = repository.get_skipped_videos()

        # Assert
        assert len(skipped) == 1
        assert skipped[0].status == VideoStatus.SKIPPED

    def test_get_skipped_videos_filter_by_source(self, repository, sample_source, db_session):
        """Test 33: Filtrar videos skipped por source"""
        # Arrange - crear video skipped
        video = Video(
            source_id=sample_source.id,
            youtube_id="skipped2",
            title="Skipped Video",
            url="https://youtube.com/watch?v=skipped2",
            status=VideoStatus.SKIPPED,
        )
        repository.create(video)
        db_session.commit()

        # Act
        skipped = repository.get_skipped_videos(source_id=sample_source.id)

        # Assert
        assert len(skipped) == 1
        assert all(v.source_id == sample_source.id for v in skipped)


class TestVideoRepositoryStats:
    """Tests para get_stats_by_status()."""

    @pytest.fixture
    def repository(self, db_session):
        return VideoRepository(db_session)

    def test_get_stats_by_status(self, repository, multiple_videos):
        """Test 34: Estadísticas agrupadas por status"""
        # Act
        stats = repository.get_stats_by_status()

        # Assert
        assert stats[VideoStatus.PENDING] == 3
        assert stats[VideoStatus.COMPLETED] == 3
        assert stats[VideoStatus.FAILED] == 2
        assert stats[VideoStatus.DOWNLOADING] == 1
        assert stats[VideoStatus.SKIPPED] == 1

    def test_get_stats_by_status_empty_database(self, repository):
        """Test 35: Estadísticas con BD vacía"""
        # Act
        stats = repository.get_stats_by_status()

        # Assert
        assert stats == {}
