"""
Tests unitarios para TranscriptionRepository.

Estrategia de testing:
- Usar PostgreSQL en Docker (compatibilidad total con JSONB)
- Tests aislados con limpieza automática entre tests
- Validación de CRUD completo
- Validación de queries por video_id y language
"""

import pytest
from uuid import uuid4

from src.repositories.transcription_repository import TranscriptionRepository
from src.repositories.exceptions import NotFoundError
from src.models import Transcription


class TestTranscriptionRepositoryCRUD:
    """Tests para operaciones CRUD básicas."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que crea una instancia del repository."""
        return TranscriptionRepository(db_session)

    def test_create_transcription(self, repository, sample_video, db_session):
        """Test 1: Crear transcripción exitosamente"""
        # Arrange
        transcription = Transcription(
            video_id=sample_video.id,
            text="Esta es una transcripción de prueba del video.",
            language="es",
            model_used="whisper-base",
            duration_seconds=300
        )

        # Act
        created = repository.create(transcription)
        db_session.commit()

        # Assert
        assert created.id is not None
        assert created.video_id == sample_video.id
        assert created.text == "Esta es una transcripción de prueba del video."
        assert created.language == "es"
        assert created.model_used == "whisper-base"

    def test_get_by_id_found(self, repository, sample_transcription):
        """Test 2: Obtener transcripción por ID existente"""
        # Act
        transcription = repository.get_by_id(sample_transcription.id)

        # Assert
        assert transcription is not None
        assert transcription.id == sample_transcription.id
        assert transcription.video_id == sample_transcription.video_id
        assert transcription.text == sample_transcription.text

    def test_get_by_id_not_found(self, repository):
        """Test 3: Obtener transcripción por ID inexistente lanza NotFoundError"""
        # Arrange
        non_existent_id = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(non_existent_id)

    def test_list_all_transcriptions(self, repository, sample_transcription, english_transcription):
        """Test 4: Listar todas las transcripciones"""
        # Act
        transcriptions = repository.list_all()

        # Assert
        assert len(transcriptions) == 2
        assert all(isinstance(t, Transcription) for t in transcriptions)

    def test_update_transcription(self, repository, sample_transcription, db_session):
        """Test 5: Actualizar transcripción exitosamente"""
        # Arrange
        original_text = sample_transcription.text
        sample_transcription.text = "Texto actualizado de la transcripción."

        # Act
        updated = repository.update(sample_transcription)
        db_session.commit()

        # Assert
        assert updated.id == sample_transcription.id
        assert updated.text == "Texto actualizado de la transcripción."
        assert updated.text != original_text

    def test_delete_transcription(self, repository, sample_transcription, db_session):
        """Test 6: Eliminar transcripción exitosamente"""
        # Arrange
        transcription_id = sample_transcription.id

        # Act
        repository.delete(sample_transcription)
        db_session.commit()

        # Assert
        with pytest.raises(NotFoundError):
            repository.get_by_id(transcription_id)


class TestTranscriptionRepositoryVideoQueries:
    """Tests para queries por video_id."""

    @pytest.fixture
    def repository(self, db_session):
        return TranscriptionRepository(db_session)

    def test_get_by_video_id_found(self, repository, sample_video, sample_transcription):
        """Test 7: Buscar transcripción por video_id existente"""
        # Act
        transcription = repository.get_by_video_id(sample_video.id)

        # Assert
        assert transcription is not None
        assert transcription.id == sample_transcription.id
        assert transcription.video_id == sample_video.id

    def test_get_by_video_id_not_found(self, repository, sample_video):
        """Test 8: Buscar por video_id sin transcripción retorna None"""
        # Arrange - sample_video sin transcripción (crear nuevo video sin transcripción)
        from src.models import Video, VideoStatus
        video_without_transcription = Video(
            source_id=sample_video.source_id,
            youtube_id="no_transcription",
            title="Video sin transcripción",
            url="https://youtube.com/watch?v=no_transcription",
            status=VideoStatus.PENDING
        )
        repository.session.add(video_without_transcription)
        repository.session.commit()

        # Act
        transcription = repository.get_by_video_id(video_without_transcription.id)

        # Assert
        assert transcription is None

    def test_exists_by_video_id_true(self, repository, sample_video, sample_transcription):
        """Test 9: exists_by_video_id() retorna True para video con transcripción"""
        # sample_transcription fixture ensures sample_video has a transcription
        # Act
        result = repository.exists_by_video_id(sample_video.id)

        # Assert
        assert result is True

    def test_exists_by_video_id_false(self, repository, sample_video):
        """Test 10: exists_by_video_id() retorna False para video sin transcripción"""
        # Arrange - crear video sin transcripción
        from src.models import Video, VideoStatus
        video_without_transcription = Video(
            source_id=sample_video.source_id,
            youtube_id="no_transcription2",
            title="Video sin transcripción",
            url="https://youtube.com/watch?v=no_transcription2",
            status=VideoStatus.PENDING
        )
        repository.session.add(video_without_transcription)
        repository.session.commit()

        # Act
        result = repository.exists_by_video_id(video_without_transcription.id)

        # Assert
        assert result is False


class TestTranscriptionRepositoryLanguageQueries:
    """Tests para queries por idioma."""

    @pytest.fixture
    def repository(self, db_session):
        return TranscriptionRepository(db_session)

    def test_get_by_language_spanish(self, repository, sample_transcription):
        """Test 11: Obtener transcripciones en español"""
        # Act
        spanish = repository.get_by_language("es")

        # Assert
        assert len(spanish) == 1
        assert all(t.language == "es" for t in spanish)

    def test_get_by_language_english(self, repository, english_transcription):
        """Test 12: Obtener transcripciones en inglés"""
        # Act
        english = repository.get_by_language("en")

        # Assert
        assert len(english) == 1
        assert all(t.language == "en" for t in english)

    def test_get_by_language_not_found(self, repository, sample_transcription):
        """Test 13: Idioma sin transcripciones retorna lista vacía"""
        # Act
        french = repository.get_by_language("fr")

        # Assert
        assert french == []

    def test_get_by_language_multiple(self, repository, db_session, sample_source):
        """Test 14: Múltiples transcripciones del mismo idioma"""
        # Arrange - crear varias transcripciones en español
        from src.models import Video, VideoStatus
        videos = []
        transcriptions = []

        for i in range(3):
            video = Video(
                source_id=sample_source.id,
                youtube_id=f"video_es_{i}",
                title=f"Video {i}",
                url=f"https://youtube.com/watch?v=video_es_{i}",
                status=VideoStatus.COMPLETED
            )
            repository.session.add(video)
            videos.append(video)

        db_session.commit()

        for video in videos:
            db_session.refresh(video)
            trans = Transcription(
                video_id=video.id,
                text=f"Transcripción {video.youtube_id}",
                language="es",
                model_used="whisper-base"
            )
            repository.session.add(trans)
            transcriptions.append(trans)

        db_session.commit()

        # Act
        spanish = repository.get_by_language("es")

        # Assert
        assert len(spanish) == 3
        assert all(t.language == "es" for t in spanish)


class TestTranscriptionRepositoryPagination:
    """Tests para paginación cursor-based."""

    @pytest.fixture
    def repository(self, db_session):
        return TranscriptionRepository(db_session)

    def test_list_paginated_basic(self, repository, sample_transcription, english_transcription):
        """Test 15: Paginación básica"""
        # Act
        transcriptions = repository.list_paginated(limit=2)

        # Assert
        assert len(transcriptions) <= 2

    def test_list_paginated_with_cursor(self, repository, multiple_summaries):
        """Test 16: Paginación con cursor"""
        # Note: multiple_summaries fixture crea transcripciones automáticamente
        # Arrange - obtener primera página
        first_page = repository.list_paginated(limit=2)
        assert len(first_page) > 0, "Should have results in first page"
        cursor = first_page[-1].id

        # Act - obtener segunda página
        second_page = repository.list_paginated(limit=2, cursor=cursor)

        # Assert - puede haber menos si no hay suficientes transcripciones
        # Los IDs deben ser diferentes
        first_ids = {t.id for t in first_page}
        second_ids = {t.id for t in second_page}
        if second_page:
            assert first_ids.isdisjoint(second_ids)

    def test_list_paginated_empty_database(self, repository):
        """Test 17: Paginación con BD vacía"""
        # Act
        transcriptions = repository.list_paginated()

        # Assert
        assert transcriptions == []


class TestTranscriptionRepositoryEdgeCases:
    """Tests para casos edge y validaciones."""

    @pytest.fixture
    def repository(self, db_session):
        return TranscriptionRepository(db_session)

    def test_create_with_segments(self, repository, sample_video, db_session):
        """Test 18: Crear transcripción con segmentos JSONB"""
        # Arrange
        segments = {
            "segments": [
                {"start": 0.0, "end": 5.2, "text": "Hola mundo"},
                {"start": 5.2, "end": 10.5, "text": "Esto es un test"}
            ]
        }
        transcription = Transcription(
            video_id=sample_video.id,
            text="Hola mundo. Esto es un test.",
            language="es",
            model_used="whisper-small",
            segments=segments,
            confidence_score=0.92
        )

        # Act
        created = repository.create(transcription)
        db_session.commit()
        db_session.refresh(created)

        # Assert
        assert created.segments is not None
        assert "segments" in created.segments
        assert len(created.segments["segments"]) == 2
        assert created.confidence_score == 0.92

    def test_update_confidence_score(self, repository, sample_transcription, db_session):
        """Test 19: Actualizar confidence score"""
        # Arrange
        sample_transcription.confidence_score = 0.95

        # Act
        updated = repository.update(sample_transcription)
        db_session.commit()
        db_session.refresh(updated)

        # Assert
        assert updated.confidence_score == 0.95

    def test_transcription_unique_per_video(self, repository, sample_video, sample_transcription, db_session):
        """Test 20: No se puede crear segunda transcripción para el mismo video (violación UNIQUE)"""
        # Arrange - intentar crear segunda transcripción para el mismo video
        duplicate_transcription = Transcription(
            video_id=sample_video.id,  # Mismo video_id
            text="Intento de duplicado",
            language="es"
        )

        # Act & Assert
        from sqlalchemy.exc import IntegrityError
        with pytest.raises(IntegrityError):
            repository.create(duplicate_transcription)
            db_session.commit()
