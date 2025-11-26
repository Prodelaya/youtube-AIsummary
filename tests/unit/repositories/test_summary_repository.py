"""
Tests unitarios para SummaryRepository.

Estrategia de testing:
- Usar PostgreSQL en Docker (compatibilidad total con ARRAY, JSONB)
- Tests aislados con limpieza automática entre tests
- Validación de CRUD completo
- Validación de búsqueda full-text con PostgreSQL
- Validación de invalidación de caché
"""

from unittest.mock import Mock, patch
from uuid import uuid4

import pytest

from src.models import Summary
from src.repositories.summary_repository import SummaryRepository


class TestSummaryRepositoryCRUD:
    """Tests para operaciones CRUD básicas."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que crea una instancia del repository."""
        return SummaryRepository(db_session)

    def test_create_summary(self, repository, sample_transcription, db_session):
        """Test 1: Crear resumen exitosamente"""
        # Arrange
        summary = Summary(
            transcription_id=sample_transcription.id,
            summary_text="Este es un resumen de prueba del video sobre FastAPI.",
            keywords=["FastAPI", "Python", "API"],
            category="framework",
        )

        # Act
        created = repository.create(summary)
        db_session.commit()

        # Assert
        assert created.id is not None
        assert created.transcription_id == sample_transcription.id
        assert created.summary_text == "Este es un resumen de prueba del video sobre FastAPI."
        assert created.keywords == ["FastAPI", "Python", "API"]
        assert created.category == "framework"

    def test_get_by_id_found_no_cache(self, repository, sample_summary):
        """Test 2: Obtener resumen por ID sin caché"""
        # Act - usar use_cache=False para evitar mock de cache_service
        summary = repository.get_by_id(sample_summary.id, use_cache=False)

        # Assert
        assert summary is not None
        assert summary.id == sample_summary.id
        assert summary.summary_text == sample_summary.summary_text

    def test_get_by_id_not_found(self, repository):
        """Test 3: Obtener resumen por ID inexistente con use_cache=False"""
        # Arrange
        non_existent_id = uuid4()

        # Act
        summary = repository.get_by_id(non_existent_id, use_cache=False)

        # Assert
        assert summary is None

    def test_list_all_summaries(self, repository, multiple_summaries):
        """Test 4: Listar todos los resúmenes"""
        # Act
        summaries = repository.list_all()

        # Assert
        assert len(summaries) == 5
        assert all(isinstance(s, Summary) for s in summaries)

    def test_update_summary(self, repository, sample_summary, db_session):
        """Test 5: Actualizar resumen exitosamente"""
        # Arrange
        original_text = sample_summary.summary_text
        sample_summary.summary_text = "Texto actualizado del resumen."

        # Act
        updated = repository.update(sample_summary)
        db_session.commit()

        # Assert
        assert updated.id == sample_summary.id
        assert updated.summary_text == "Texto actualizado del resumen."
        assert updated.summary_text != original_text

    def test_delete_summary(self, repository, sample_summary, db_session):
        """Test 6: Eliminar resumen exitosamente"""
        # Arrange
        summary_id = sample_summary.id

        # Act
        repository.delete(sample_summary)
        db_session.commit()

        # Assert
        summary = repository.get_by_id(summary_id, use_cache=False)
        assert summary is None


class TestSummaryRepositoryTranscriptionQueries:
    """Tests para queries por transcription_id."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_get_by_transcription_id_found(self, repository, sample_transcription, sample_summary):
        """Test 7: Buscar resumen por transcription_id existente"""
        # Act
        summary = repository.get_by_transcription_id(sample_transcription.id)

        # Assert
        assert summary is not None
        assert summary.id == sample_summary.id
        assert summary.transcription_id == sample_transcription.id

    def test_get_by_transcription_id_not_found(self, repository, sample_transcription):
        """Test 8: Buscar por transcription_id sin resumen retorna None"""
        # Arrange - crear nueva transcripción sin resumen
        from src.models import Transcription, Video, VideoStatus

        video = Video(
            source_id=sample_transcription.video.source_id,
            youtube_id="no_summary",
            title="Video sin resumen",
            url="https://youtube.com/watch?v=no_summary",
            status=VideoStatus.COMPLETED,
        )
        repository.session.add(video)
        repository.session.commit()
        repository.session.refresh(video)

        transcription = Transcription(
            video_id=video.id, text="Transcripción sin resumen", language="es"
        )
        repository.session.add(transcription)
        repository.session.commit()
        repository.session.refresh(transcription)

        # Act
        summary = repository.get_by_transcription_id(transcription.id)

        # Assert
        assert summary is None


class TestSummaryRepositoryRecent:
    """Tests para get_recent()."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_get_recent_basic(self, repository, multiple_summaries):
        """Test 9: Obtener resúmenes recientes básico"""
        # Act
        recent = repository.get_recent(limit=3)

        # Assert
        assert len(recent) == 3
        # Verificar orden descendente por created_at
        for i in range(len(recent) - 1):
            assert recent[i].created_at >= recent[i + 1].created_at

    def test_get_recent_with_relations(self, repository, multiple_summaries):
        """Test 10: Obtener recientes con relaciones cargadas"""
        # Act
        recent = repository.get_recent(limit=2, with_relations=True)

        # Assert
        assert len(recent) == 2
        # Verificar que las relaciones están cargadas
        for summary in recent:
            # El acceso a transcription.video.source no debe causar queries adicionales
            assert summary.transcription is not None
            assert summary.transcription.video is not None

    def test_get_recent_empty_database(self, repository):
        """Test 11: Obtener recientes con BD vacía"""
        # Act
        recent = repository.get_recent()

        # Assert
        assert recent == []


class TestSummaryRepositoryCategoryAndKeywords:
    """Tests para filtrado por categoría y keywords."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_get_by_category(self, repository, db_session, sample_transcription):
        """Test 12: Filtrar resúmenes por categoría"""
        # Arrange - crear resúmenes con diferentes categorías
        from src.models import Transcription, Video, VideoStatus

        categories_data = [
            ("framework", ["FastAPI"]),
            ("framework", ["Django"]),
            ("language", ["Python"]),
            ("tool", ["Docker"]),
        ]

        for i, (category, keywords) in enumerate(categories_data):
            video = Video(
                source_id=sample_transcription.video.source_id,
                youtube_id=f"cat_test_{i}",
                title=f"Video {i}",
                url=f"https://youtube.com/watch?v=cat_test_{i}",
                status=VideoStatus.COMPLETED,
            )
            repository.session.add(video)
            repository.session.commit()
            repository.session.refresh(video)

            trans = Transcription(video_id=video.id, text=f"Transcription {i}", language="es")
            repository.session.add(trans)
            repository.session.commit()
            repository.session.refresh(trans)

            summary = Summary(
                transcription_id=trans.id,
                summary_text=f"Summary {i}",
                keywords=keywords,
                category=category,
            )
            repository.session.add(summary)

        db_session.commit()

        # Act
        frameworks = repository.get_by_category("framework")

        # Assert
        assert len(frameworks) == 2
        assert all(s.category == "framework" for s in frameworks)

    def test_search_by_keyword(self, repository, multiple_summaries):
        """Test 13: Buscar resúmenes por keyword específico"""
        # Act - buscar keyword "Python" que está en varios resúmenes
        python_summaries = repository.search_by_keyword("Python")

        # Assert
        assert len(python_summaries) >= 1
        # Verificar que todos contienen el keyword
        for summary in python_summaries:
            assert summary.keywords is not None
            assert "Python" in summary.keywords

    def test_search_by_keyword_not_found(self, repository, multiple_summaries):
        """Test 14: Buscar keyword inexistente retorna lista vacía"""
        # Act
        results = repository.search_by_keyword("NonExistentKeyword")

        # Assert
        assert results == []


class TestSummaryRepositoryTelegram:
    """Tests para funcionalidad de Telegram."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_get_unsent_to_telegram(self, repository, sample_summary, db_session):
        """Test 15: Obtener resúmenes no enviados a Telegram"""
        # Arrange - crear resumen no enviado
        from src.models import Summary, Transcription, Video, VideoStatus

        video = Video(
            source_id=sample_summary.transcription.video.source_id,
            youtube_id="unsent_test",
            title="Unsent Video",
            url="https://youtube.com/watch?v=unsent_test",
            status=VideoStatus.COMPLETED,
        )
        repository.session.add(video)
        db_session.commit()
        db_session.refresh(video)

        trans = Transcription(video_id=video.id, text="Transcription for unsent", language="es")
        repository.session.add(trans)
        db_session.commit()
        db_session.refresh(trans)

        unsent_summary = Summary(
            transcription_id=trans.id, summary_text="This should be sent", sent_to_telegram=False
        )
        repository.session.add(unsent_summary)
        db_session.commit()

        # Act
        unsent = repository.get_unsent_to_telegram()

        # Assert
        assert len(unsent) >= 1
        assert all(not s.sent_to_telegram for s in unsent)

    def test_mark_as_sent(self, repository, sample_summary, db_session):
        """Test 16: Marcar resumen como enviado"""
        # Arrange
        assert sample_summary.sent_to_telegram is False

        # Act
        repository.mark_as_sent(sample_summary.id)
        db_session.refresh(sample_summary)

        # Assert
        assert sample_summary.sent_to_telegram is True
        assert sample_summary.sent_at is not None


class TestSummaryRepositoryPagination:
    """Tests para paginación cursor-based."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_list_paginated_basic(self, repository, multiple_summaries):
        """Test 17: Paginación básica"""
        # Act
        summaries = repository.list_paginated(limit=3)

        # Assert
        assert len(summaries) == 3

    def test_list_paginated_with_cursor(self, repository, multiple_summaries):
        """Test 18: Paginación con cursor"""
        # Arrange - obtener primera página
        first_page = repository.list_paginated(limit=2)
        assert len(first_page) > 0, "Should have results in first page"
        cursor = first_page[-1].id

        # Act - obtener segunda página
        second_page = repository.list_paginated(limit=2, cursor=cursor)

        # Assert
        first_ids = {s.id for s in first_page}
        second_ids = {s.id for s in second_page}
        if second_page:
            assert first_ids.isdisjoint(second_ids)


class TestSummaryRepositoryVideoQueries:
    """Tests para get_by_video_id()."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_get_by_video_id_found(self, repository, sample_video, sample_summary):
        """Test 19: Buscar resumen por video_id"""
        # Act
        summary = repository.get_by_video_id(sample_video.id)

        # Assert
        assert summary is not None
        assert summary.id == sample_summary.id

    def test_get_by_video_id_not_found(self, repository, db_session):
        """Test 20: Buscar por video_id sin resumen retorna None"""
        # Arrange - crear video sin resumen
        from src.models import Source, Video, VideoStatus

        source = Source(
            name="Test Source", source_type="youtube", url="https://youtube.com/@test", active=True
        )
        repository.session.add(source)
        db_session.commit()
        db_session.refresh(source)

        video = Video(
            source_id=source.id,
            youtube_id="no_summary_vid",
            title="Video without summary",
            url="https://youtube.com/watch?v=no_summary_vid",
            status=VideoStatus.PENDING,
        )
        repository.session.add(video)
        db_session.commit()
        db_session.refresh(video)

        # Act
        summary = repository.get_by_video_id(video.id)

        # Assert
        assert summary is None


class TestSummaryRepositoryFullTextSearch:
    """Tests para búsqueda full-text."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_search_by_text_basic_no_cache(self, repository, multiple_summaries):
        """Test 21: Búsqueda full-text básica sin caché"""
        # Act - buscar "FastAPI" que está en uno de los resúmenes
        results = repository.search_by_text("FastAPI", limit=10, use_cache=False)

        # Assert
        assert len(results) >= 1
        # Verificar que los resultados contienen el término buscado
        for summary in results:
            text_lower = summary.summary_text.lower()
            keywords_lower = [k.lower() for k in (summary.keywords or [])]
            assert "fastapi" in text_lower or "fastapi" in keywords_lower

    def test_search_by_text_no_results(self, repository, multiple_summaries):
        """Test 22: Búsqueda sin resultados retorna lista vacía"""
        # Act
        results = repository.search_by_text("XYZ123NonExistent", use_cache=False)

        # Assert
        assert results == []

    def test_search_full_text_with_ranking(self, repository, multiple_summaries):
        """Test 23: Búsqueda full-text con ranking de relevancia"""
        # Act
        results = repository.search_full_text("Python", limit=10)

        # Assert
        if len(results) > 0:
            # Verificar estructura de resultados
            for result in results:
                assert "summary" in result
                assert "relevance_score" in result
                assert "id" in result
                assert isinstance(result["relevance_score"], float)
                assert result["relevance_score"] > 0

            # Verificar orden por relevancia (descendente)
            if len(results) > 1:
                for i in range(len(results) - 1):
                    assert results[i]["relevance_score"] >= results[i + 1]["relevance_score"]


class TestSummaryRepositoryCacheInvalidation:
    """Tests para invalidación de caché."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_invalidate_summary_cache(self, repository, sample_summary):
        """Test 24: Invalidar caché de un resumen específico"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            mock_cache.delete = Mock(return_value=True)

            # Act
            repository.invalidate_summary_cache(sample_summary.id)

            # Assert
            mock_cache.delete.assert_called_once_with(f"summary:detail:{sample_summary.id}")

    def test_invalidate_search_cache_all(self, repository):
        """Test 25: Invalidar todo el caché de búsquedas"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            mock_cache.invalidate_pattern = Mock(return_value=5)

            # Act
            repository.invalidate_search_cache()

            # Assert
            mock_cache.invalidate_pattern.assert_called_once_with("search:*:results:*")

    def test_invalidate_search_cache_keywords(self, repository):
        """Test 26: Invalidar caché de búsquedas por keywords"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            with patch("src.services.cache_service.hash_query") as mock_hash:
                mock_hash.return_value = "hash123"
                mock_cache.invalidate_pattern = Mock(return_value=2)

                # Act
                repository.invalidate_search_cache(keywords=["FastAPI", "Python"])

                # Assert
                assert mock_cache.invalidate_pattern.call_count == 2

    def test_invalidate_recent_cache(self, repository):
        """Test 27: Invalidar caché de resúmenes recientes"""
        # Arrange
        with patch("src.services.cache_service.cache_service") as mock_cache:
            mock_cache.invalidate_pattern = Mock(return_value=10)

            # Act
            repository.invalidate_recent_cache()

            # Assert
            mock_cache.invalidate_pattern.assert_called_once_with("user:*:recent")


class TestSummaryRepositoryEdgeCases:
    """Tests para casos edge y validaciones."""

    @pytest.fixture
    def repository(self, db_session):
        return SummaryRepository(db_session)

    def test_create_with_metadata(self, repository, sample_transcription, db_session):
        """Test 28: Crear resumen con metadata JSONB completa"""
        # Arrange
        metadata = {"temperature": 0.7, "max_tokens": 1000, "model_version": "v2"}
        summary = Summary(
            transcription_id=sample_transcription.id,
            summary_text="Resumen con metadata completa",
            keywords=["test", "metadata"],
            category="tool",
            tokens_used=850,
            input_tokens=700,
            output_tokens=150,
            processing_time_ms=2500,
            extra_metadata=metadata,
        )

        # Act
        created = repository.create(summary)
        db_session.commit()
        db_session.refresh(created)

        # Assert
        assert created.extra_metadata is not None
        assert created.extra_metadata["temperature"] == 0.7
        assert created.tokens_used == 850
        assert created.processing_time_ms == 2500

    def test_summary_unique_per_transcription(
        self, repository, sample_transcription, sample_summary, db_session
    ):
        """Test 29: No se puede crear segundo resumen para misma transcripción (violación UNIQUE)"""
        # Arrange - intentar crear segundo resumen para misma transcripción
        duplicate_summary = Summary(
            transcription_id=sample_transcription.id,  # Mismo transcription_id
            summary_text="Intento de duplicado",
        )

        # Act & Assert
        from sqlalchemy.exc import IntegrityError

        with pytest.raises(IntegrityError):
            repository.create(duplicate_summary)
            db_session.commit()

    def test_list_all_with_limit(self, repository, multiple_summaries):
        """Test 30: Listar con límite"""
        # Act
        summaries = repository.list_all(limit=2)

        # Assert
        assert len(summaries) == 2
