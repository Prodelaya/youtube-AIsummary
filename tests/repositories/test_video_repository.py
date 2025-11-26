"""
Tests de integración para VideoRepository.

Estos tests validan el comportamiento del VideoRepository
usando una base de datos real de PostgreSQL con transacciones
que se revierten automáticamente al finalizar cada test.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.models import Video, VideoStatus
from src.repositories.exceptions import NotFoundError
from src.repositories.video_repository import VideoRepository


class TestVideoRepositoryInheritance:
    """Tests que validan la herencia de BaseRepository."""

    def test_create_video_inherited(self, db_session, sample_source):
        """create() heredado de BaseRepository debe funcionar correctamente."""
        # Arrange
        repo = VideoRepository(db_session)
        video = Video(
            source_id=sample_source.id,
            youtube_id="new_video_123",
            title="New Video",
            url="https://youtube.com/watch?v=new123",
            duration_seconds=450,
            status=VideoStatus.PENDING,
            published_at=datetime.now(UTC),
        )

        # Act
        created = repo.create(video)

        # Assert
        assert created.id is not None
        assert created.youtube_id == "new_video_123"
        assert created.source_id == sample_source.id
        assert created.status == VideoStatus.PENDING
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_get_by_id_success_inherited(self, db_session, sample_video):
        """get_by_id() heredado debe retornar video existente."""
        # Arrange
        repo = VideoRepository(db_session)

        # Act
        found = repo.get_by_id(sample_video.id)

        # Assert
        assert found.id == sample_video.id
        assert found.youtube_id == sample_video.youtube_id
        assert found.title == sample_video.title

    def test_get_by_id_not_found_inherited(self, db_session):
        """get_by_id() debe lanzar NotFoundError cuando no existe."""
        # Arrange
        repo = VideoRepository(db_session)
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            repo.get_by_id(non_existent_id)

        assert exc_info.value.resource_type == "Video"
        assert exc_info.value.resource_id == non_existent_id

    def test_update_video_inherited(self, db_session, sample_video):
        """update() heredado debe actualizar correctamente."""
        # Arrange
        repo = VideoRepository(db_session)
        original_status = sample_video.status

        # Act
        sample_video.status = VideoStatus.COMPLETED
        updated = repo.update(sample_video)

        # Assert
        assert updated.status == VideoStatus.COMPLETED
        assert updated.status != original_status
        assert updated.id == sample_video.id

    def test_delete_video_inherited(self, db_session, sample_video):
        """delete() heredado debe eliminar correctamente."""
        # Arrange
        repo = VideoRepository(db_session)
        video_id = sample_video.id

        # Act
        repo.delete(sample_video)

        # Assert - Verificar que ya no existe
        with pytest.raises(NotFoundError):
            repo.get_by_id(video_id)


class TestVideoRepositoryGetByStatus:
    """Tests para el método get_by_status()."""

    def test_get_by_status_pending(self, db_session, sample_source, video_factory):
        """get_by_status() debe retornar solo videos PENDING."""
        # Arrange
        repo = VideoRepository(db_session)
        pending1 = video_factory(
            source_id=sample_source.id,
            youtube_id="pending1",
            title="Pending 1",
            status=VideoStatus.PENDING,
        )
        pending2 = video_factory(
            source_id=sample_source.id,
            youtube_id="pending2",
            title="Pending 2",
            status=VideoStatus.PENDING,
        )
        completed = video_factory(
            source_id=sample_source.id,
            youtube_id="completed1",
            title="Completed 1",
            status=VideoStatus.COMPLETED,
        )

        # Act
        pending_videos = repo.get_by_status(VideoStatus.PENDING)

        # Assert
        pending_ids = [v.id for v in pending_videos]
        assert pending1.id in pending_ids
        assert pending2.id in pending_ids
        assert completed.id not in pending_ids

        # Verificar que todos son PENDING
        for video in pending_videos:
            assert video.status == VideoStatus.PENDING

    def test_get_by_status_completed(self, db_session, sample_source, video_factory):
        """get_by_status() debe retornar solo videos COMPLETED."""
        # Arrange
        repo = VideoRepository(db_session)
        completed1 = video_factory(
            source_id=sample_source.id,
            youtube_id="comp1",
            status=VideoStatus.COMPLETED,
        )
        completed2 = video_factory(
            source_id=sample_source.id,
            youtube_id="comp2",
            status=VideoStatus.COMPLETED,
        )
        pending = video_factory(
            source_id=sample_source.id, youtube_id="pend1", status=VideoStatus.PENDING
        )

        # Act
        completed_videos = repo.get_by_status(VideoStatus.COMPLETED)

        # Assert
        completed_ids = [v.id for v in completed_videos]
        assert completed1.id in completed_ids
        assert completed2.id in completed_ids
        assert pending.id not in completed_ids

    def test_get_by_status_failed(self, db_session, sample_source, video_factory):
        """get_by_status() debe retornar solo videos FAILED."""
        # Arrange
        repo = VideoRepository(db_session)
        failed1 = video_factory(
            source_id=sample_source.id, youtube_id="fail1", status=VideoStatus.FAILED
        )
        failed2 = video_factory(
            source_id=sample_source.id, youtube_id="fail2", status=VideoStatus.FAILED
        )
        pending = video_factory(
            source_id=sample_source.id, youtube_id="pend1", status=VideoStatus.PENDING
        )

        # Act
        failed_videos = repo.get_by_status(VideoStatus.FAILED)

        # Assert
        failed_ids = [v.id for v in failed_videos]
        assert failed1.id in failed_ids
        assert failed2.id in failed_ids
        assert pending.id not in failed_ids

    def test_get_by_status_empty_result(self, db_session, sample_source, video_factory):
        """get_by_status() debe retornar lista vacía si no hay videos en ese estado."""
        # Arrange
        repo = VideoRepository(db_session)
        # Crear solo videos PENDING
        video_factory(source_id=sample_source.id, youtube_id="pend1", status=VideoStatus.PENDING)

        # Act - Buscar videos en DOWNLOADING (no existen)
        downloading_videos = repo.get_by_status(VideoStatus.DOWNLOADING)

        # Assert
        assert downloading_videos == []

    def test_get_by_status_all_enum_values(self, db_session, sample_source, video_factory):
        """get_by_status() debe funcionar con todos los valores de VideoStatus enum."""
        # Arrange
        repo = VideoRepository(db_session)
        # Crear un video por cada estado
        statuses = [
            VideoStatus.PENDING,
            VideoStatus.DOWNLOADING,
            VideoStatus.DOWNLOADED,
            VideoStatus.TRANSCRIBING,
            VideoStatus.TRANSCRIBED,
            VideoStatus.SUMMARIZING,
            VideoStatus.COMPLETED,
            VideoStatus.FAILED,
        ]
        created_videos = {}
        for i, status in enumerate(statuses):
            video = video_factory(
                source_id=sample_source.id,
                youtube_id=f"video_{status.value}_{i}",
                status=status,
            )
            created_videos[status] = video

        # Act & Assert - Verificar que cada estado se puede filtrar
        for status in statuses:
            videos = repo.get_by_status(status)
            video_ids = [v.id for v in videos]
            assert created_videos[status].id in video_ids


class TestVideoRepositoryGetBySource:
    """Tests para el método get_by_source()."""

    def test_get_by_source_filters_correctly(
        self, db_session, sample_source, source_factory, video_factory
    ):
        """get_by_source() debe retornar solo videos de esa source."""
        # Arrange
        repo = VideoRepository(db_session)
        other_source = source_factory(name="Other", url="https://youtube.com/@other")

        # Videos de sample_source
        video1 = video_factory(source_id=sample_source.id, youtube_id="vid1")
        video2 = video_factory(source_id=sample_source.id, youtube_id="vid2")
        # Video de otra source
        other_video = video_factory(source_id=other_source.id, youtube_id="other_vid")

        # Act
        videos = repo.get_by_source(sample_source.id)

        # Assert
        video_ids = [v.id for v in videos]
        assert video1.id in video_ids
        assert video2.id in video_ids
        assert other_video.id not in video_ids

    def test_get_by_source_ordered_by_published_at_desc(
        self, db_session, sample_source, video_factory
    ):
        """get_by_source() debe ordenar por published_at DESC (más recientes primero)."""
        # Arrange
        repo = VideoRepository(db_session)
        now = datetime.now(UTC)

        # Crear videos con fechas diferentes
        old_video = video_factory(
            source_id=sample_source.id,
            youtube_id="old",
            published_at=now - timedelta(days=10),
        )
        recent_video = video_factory(
            source_id=sample_source.id,
            youtube_id="recent",
            published_at=now - timedelta(days=1),
        )
        newest_video = video_factory(
            source_id=sample_source.id, youtube_id="newest", published_at=now
        )

        # Act
        videos = repo.get_by_source(sample_source.id)

        # Assert - Verificar orden descendente (newest primero)
        assert videos[0].id == newest_video.id
        assert videos[1].id == recent_video.id
        assert videos[2].id == old_video.id

    def test_get_by_source_pagination_default(self, db_session, sample_source, video_factory):
        """get_by_source() sin parámetros debe usar limit=100, offset=0."""
        # Arrange
        repo = VideoRepository(db_session)
        # Crear 3 videos
        for i in range(3):
            video_factory(source_id=sample_source.id, youtube_id=f"vid{i}")

        # Act
        videos = repo.get_by_source(sample_source.id)

        # Assert
        assert len(videos) >= 3

    def test_get_by_source_pagination_custom(self, db_session, sample_source, video_factory):
        """get_by_source() debe respetar limit y offset personalizados."""
        # Arrange
        repo = VideoRepository(db_session)
        now = datetime.now(UTC)

        # Crear 5 videos con fechas diferentes para orden predecible
        videos_created = []
        for i in range(5):
            video = video_factory(
                source_id=sample_source.id,
                youtube_id=f"vid{i}",
                published_at=now - timedelta(days=i),
            )
            videos_created.append(video)

        # Act
        page1 = repo.get_by_source(sample_source.id, limit=2, offset=0)
        page2 = repo.get_by_source(sample_source.id, limit=2, offset=2)

        # Assert
        assert len(page1) == 2
        assert len(page2) == 2
        # Verificar que son páginas diferentes
        page1_ids = {v.id for v in page1}
        page2_ids = {v.id for v in page2}
        assert page1_ids.isdisjoint(page2_ids)  # Sin intersección

    def test_get_by_source_empty_result(self, db_session, sample_source):
        """get_by_source() debe retornar lista vacía si la source no tiene videos."""
        # Arrange
        repo = VideoRepository(db_session)

        # Act
        videos = repo.get_by_source(sample_source.id)

        # Assert
        assert videos == []
        assert isinstance(videos, list)


class TestVideoRepositoryGetBySourceAndStatus:
    """Tests para el método get_by_source_and_status()."""

    def test_get_by_source_and_status_filters_both(self, db_session, sample_source, video_factory):
        """get_by_source_and_status() debe filtrar por source_id Y status."""
        # Arrange
        repo = VideoRepository(db_session)
        # Videos de sample_source con diferentes estados
        pending = video_factory(
            source_id=sample_source.id, youtube_id="pend1", status=VideoStatus.PENDING
        )
        completed = video_factory(
            source_id=sample_source.id, youtube_id="comp1", status=VideoStatus.COMPLETED
        )
        failed = video_factory(
            source_id=sample_source.id, youtube_id="fail1", status=VideoStatus.FAILED
        )

        # Act
        pending_videos = repo.get_by_source_and_status(sample_source.id, VideoStatus.PENDING)

        # Assert
        pending_ids = [v.id for v in pending_videos]
        assert pending.id in pending_ids
        assert completed.id not in pending_ids
        assert failed.id not in pending_ids

    def test_get_by_source_and_status_filters_out_other_sources(
        self, db_session, sample_source, source_factory, video_factory
    ):
        """get_by_source_and_status() no debe retornar videos de otras sources."""
        # Arrange
        repo = VideoRepository(db_session)
        other_source = source_factory(name="Other", url="https://youtube.com/@other")

        # Video PENDING de sample_source
        video_sample = video_factory(
            source_id=sample_source.id, youtube_id="vid1", status=VideoStatus.PENDING
        )
        # Video PENDING de otra source
        video_other = video_factory(
            source_id=other_source.id, youtube_id="vid2", status=VideoStatus.PENDING
        )

        # Act
        videos = repo.get_by_source_and_status(sample_source.id, VideoStatus.PENDING)

        # Assert
        video_ids = [v.id for v in videos]
        assert video_sample.id in video_ids
        assert video_other.id not in video_ids

    def test_get_by_source_and_status_empty_result(self, db_session, sample_source, video_factory):
        """get_by_source_and_status() debe retornar lista vacía si no hay match."""
        # Arrange
        repo = VideoRepository(db_session)
        # Crear video PENDING
        video_factory(source_id=sample_source.id, youtube_id="pend1", status=VideoStatus.PENDING)

        # Act - Buscar COMPLETED (no existe)
        videos = repo.get_by_source_and_status(sample_source.id, VideoStatus.COMPLETED)

        # Assert
        assert videos == []

    def test_get_by_source_and_status_multiple_matches(
        self, db_session, sample_source, video_factory
    ):
        """get_by_source_and_status() debe retornar múltiples videos que cumplen criterios."""
        # Arrange
        repo = VideoRepository(db_session)
        pending1 = video_factory(
            source_id=sample_source.id, youtube_id="pend1", status=VideoStatus.PENDING
        )
        pending2 = video_factory(
            source_id=sample_source.id, youtube_id="pend2", status=VideoStatus.PENDING
        )
        pending3 = video_factory(
            source_id=sample_source.id, youtube_id="pend3", status=VideoStatus.PENDING
        )

        # Act
        videos = repo.get_by_source_and_status(sample_source.id, VideoStatus.PENDING)

        # Assert
        assert len(videos) == 3
        video_ids = [v.id for v in videos]
        assert pending1.id in video_ids
        assert pending2.id in video_ids
        assert pending3.id in video_ids


class TestVideoRepositoryGetByYoutubeId:
    """Tests para el método get_by_youtube_id()."""

    def test_get_by_youtube_id_finds_existing_video(self, db_session, sample_video):
        """get_by_youtube_id() debe encontrar video existente."""
        # Arrange
        repo = VideoRepository(db_session)

        # Act
        found = repo.get_by_youtube_id(sample_video.youtube_id)

        # Assert
        assert found is not None
        assert found.id == sample_video.id
        assert found.youtube_id == sample_video.youtube_id

    def test_get_by_youtube_id_returns_none_when_not_found(self, db_session):
        """get_by_youtube_id() debe retornar None cuando no existe."""
        # Arrange
        repo = VideoRepository(db_session)
        non_existent_id = "nonexistent_yt_id"

        # Act
        result = repo.get_by_youtube_id(non_existent_id)

        # Assert
        assert result is None

    def test_get_by_youtube_id_exact_match(self, db_session, sample_source, video_factory):
        """get_by_youtube_id() debe hacer match exacto."""
        # Arrange
        repo = VideoRepository(db_session)
        video = video_factory(source_id=sample_source.id, youtube_id="ExactMatch123")

        # Act
        found_exact = repo.get_by_youtube_id("ExactMatch123")
        found_different = repo.get_by_youtube_id("exactmatch123")  # Diferente case

        # Assert
        assert found_exact is not None
        assert found_exact.id == video.id
        # SQLAlchemy String es case-sensitive por defecto
        assert found_different is None

    def test_get_by_youtube_id_with_multiple_videos(self, db_session, sample_source, video_factory):
        """get_by_youtube_id() debe retornar solo el video correcto entre múltiples."""
        # Arrange
        repo = VideoRepository(db_session)
        video_factory(source_id=sample_source.id, youtube_id="vid1")
        video2 = video_factory(source_id=sample_source.id, youtube_id="vid2")
        video_factory(source_id=sample_source.id, youtube_id="vid3")

        # Act
        found = repo.get_by_youtube_id("vid2")

        # Assert
        assert found is not None
        assert found.id == video2.id
        assert found.youtube_id == "vid2"


class TestVideoRepositoryExistsByYoutubeId:
    """Tests para el método exists_by_youtube_id()."""

    def test_exists_by_youtube_id_returns_true_when_exists(self, db_session, sample_video):
        """exists_by_youtube_id() debe retornar True cuando existe."""
        # Arrange
        repo = VideoRepository(db_session)

        # Act
        exists = repo.exists_by_youtube_id(sample_video.youtube_id)

        # Assert
        assert exists is True

    def test_exists_by_youtube_id_returns_false_when_not_exists(self, db_session):
        """exists_by_youtube_id() debe retornar False cuando no existe."""
        # Arrange
        repo = VideoRepository(db_session)
        non_existent_id = "nonexistent_yt_id"

        # Act
        exists = repo.exists_by_youtube_id(non_existent_id)

        # Assert
        assert exists is False

    def test_exists_by_youtube_id_exact_match(self, db_session, sample_source, video_factory):
        """exists_by_youtube_id() debe hacer match exacto (case-sensitive)."""
        # Arrange
        repo = VideoRepository(db_session)
        video_factory(source_id=sample_source.id, youtube_id="ExactYtId123")

        # Act
        exists_exact = repo.exists_by_youtube_id("ExactYtId123")
        exists_different_case = repo.exists_by_youtube_id("exactytid123")

        # Assert
        assert exists_exact is True
        assert exists_different_case is False

    def test_exists_by_youtube_id_is_efficient(self, db_session, sample_video):
        """
        exists_by_youtube_id() debe ser eficiente (solo query de ID, no objeto completo).

        Este test es conceptual - verifica que el método retorna bool.
        La eficiencia real se valida revisando el código (query solo de ID).
        """
        # Arrange
        repo = VideoRepository(db_session)

        # Act
        result = repo.exists_by_youtube_id(sample_video.youtube_id)

        # Assert
        assert isinstance(result, bool)
        assert result is True


class TestVideoRepositoryRelationships:
    """Tests para validar relaciones Video -> Source."""

    def test_video_has_source_relationship(self, db_session, sample_video, sample_source):
        """Video debe tener relación con Source (foreign key)."""
        # Arrange
        repo = VideoRepository(db_session)

        # Act
        video = repo.get_by_id(sample_video.id)

        # Assert
        assert video.source_id == sample_source.id
        # Verificar que la relación lazy="joined" carga el source
        assert video.source is not None
        assert video.source.id == sample_source.id
        assert video.source.name == sample_source.name

    def test_cascade_delete_preserves_videos(self, db_session, sample_source, video_factory):
        """
        Al eliminar una Source, sus videos deben eliminarse (CASCADE).

        Nota: En el modelo Source, la relación videos tiene cascade="all, delete-orphan"
        """
        # Arrange
        repo = VideoRepository(db_session)
        video = video_factory(source_id=sample_source.id, youtube_id="cascade_test")
        video_id = video.id

        # Act - Eliminar la source
        db_session.delete(sample_source)
        db_session.commit()

        # Assert - El video debe haber sido eliminado también
        with pytest.raises(NotFoundError):
            repo.get_by_id(video_id)

    def test_video_references_correct_source(
        self, db_session, sample_source, source_factory, video_factory
    ):
        """Videos deben referenciar correctamente a su source padre."""
        # Arrange
        other_source = source_factory(name="Other", url="https://youtube.com/@other")

        video1 = video_factory(source_id=sample_source.id, youtube_id="vid1")
        video2 = video_factory(source_id=other_source.id, youtube_id="vid2")

        # Act
        repo = VideoRepository(db_session)
        found_video1 = repo.get_by_id(video1.id)
        found_video2 = repo.get_by_id(video2.id)

        # Assert
        assert found_video1.source.id == sample_source.id
        assert found_video2.source.id == other_source.id


class TestVideoRepositoryEdgeCases:
    """Tests de casos límite y validaciones."""

    def test_create_duplicate_youtube_id_raises_integrity_error(
        self, db_session, sample_video, sample_source
    ):
        """Intentar crear video con youtube_id duplicado debe fallar (constraint UNIQUE)."""
        # Arrange
        repo = VideoRepository(db_session)
        duplicate_video = Video(
            source_id=sample_source.id,
            youtube_id=sample_video.youtube_id,  # Duplicado
            title="Duplicate",
            url="https://youtube.com/watch?v=dup",
            status=VideoStatus.PENDING,
        )

        # Act & Assert
        with pytest.raises(Exception):  # IntegrityError de SQLAlchemy
            repo.create(duplicate_video)

    def test_video_with_metadata(self, db_session, sample_source):
        """Video puede crearse con metadata JSONB compleja."""
        # Arrange
        repo = VideoRepository(db_session)
        video = Video(
            source_id=sample_source.id,
            youtube_id="metadata_test",
            title="Test Video with Metadata",
            url="https://youtube.com/watch?v=meta",
            status=VideoStatus.PENDING,
            extra_metadata={
                "view_count": 1000000,
                "like_count": 50000,
                "comment_count": 1200,
                "tags": ["AI", "Machine Learning", "Python"],
                "thumbnail": "https://i.ytimg.com/vi/test/maxresdefault.jpg",
            },
        )

        # Act
        created = repo.create(video)

        # Assert
        assert created.extra_metadata["view_count"] == 1000000
        assert created.extra_metadata["like_count"] == 50000
        assert "AI" in created.extra_metadata["tags"]

    def test_video_status_transitions(self, db_session, sample_video):
        """Video puede transicionar entre diferentes estados."""
        # Arrange
        repo = VideoRepository(db_session)
        assert sample_video.status == VideoStatus.PENDING

        # Act & Assert - Simular pipeline de procesamiento
        sample_video.status = VideoStatus.DOWNLOADING
        repo.update(sample_video)
        assert repo.get_by_id(sample_video.id).status == VideoStatus.DOWNLOADING

        sample_video.status = VideoStatus.DOWNLOADED
        repo.update(sample_video)
        assert repo.get_by_id(sample_video.id).status == VideoStatus.DOWNLOADED

        sample_video.status = VideoStatus.COMPLETED
        repo.update(sample_video)
        assert repo.get_by_id(sample_video.id).status == VideoStatus.COMPLETED
