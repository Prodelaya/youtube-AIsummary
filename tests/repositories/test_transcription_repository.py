"""
Tests de integración para TranscriptionRepository.

Valida:
- Herencia correcta de BaseRepository (CRUD automático)
- Métodos específicos: get_by_video_id, exists_by_video_id, get_by_language
- Constraint UNIQUE en video_id (relación 1:1)
- Relación con Video (foreign key)
- Campo JSONB segments (None o dict complejo)
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Transcription
from src.repositories.transcription_repository import TranscriptionRepository


# ==================== TEST HERENCIA CRUD ====================


def test_create_transcription_inherited(db_session, sample_video):
    """
    Test que valida que create() heredado de BaseRepository funciona.

    Verifica:
    - TranscriptionRepository hereda correctamente BaseRepository[Transcription]
    - Método create() persiste la transcripción en BD
    - Se asigna ID automáticamente
    - Campos se guardan correctamente
    """
    repo = TranscriptionRepository(db_session)

    transcription_data = Transcription(
        video_id=sample_video.id,
        text="This is a test transcription created via repository.",
        language="en",
        model_used="whisper-small",
        duration_seconds=450,
        confidence_score=0.88,
    )

    created = repo.create(transcription_data)

    # Validar que se creó correctamente
    assert created.id is not None
    assert created.video_id == sample_video.id
    assert created.text == "This is a test transcription created via repository."
    assert created.language == "en"
    assert created.model_used == "whisper-small"
    assert created.duration_seconds == 450
    assert created.confidence_score == 0.88
    assert created.created_at is not None
    assert created.updated_at is not None


def test_get_by_id_inherited(db_session, sample_transcription):
    """
    Test que valida que get_by_id() heredado de BaseRepository funciona.

    Verifica:
    - Método get_by_id() encuentra la transcripción por UUID
    - Lanza NotFoundError si no existe
    """
    from uuid import uuid4

    from src.repositories.exceptions import NotFoundError

    repo = TranscriptionRepository(db_session)

    # Buscar transcripción existente
    found = repo.get_by_id(sample_transcription.id)
    assert found is not None
    assert found.id == sample_transcription.id
    assert found.video_id == sample_transcription.video_id

    # Buscar transcripción inexistente debe lanzar NotFoundError
    with pytest.raises(NotFoundError) as exc_info:
        repo.get_by_id(uuid4())

    assert "Transcription" in str(exc_info.value)


def test_delete_transcription_inherited(db_session, sample_transcription):
    """
    Test que valida que delete() heredado de BaseRepository funciona.

    Verifica:
    - Método delete() elimina la transcripción de BD
    - No se puede encontrar después de eliminada (usando exists())
    """
    repo = TranscriptionRepository(db_session)

    transcription_id = sample_transcription.id

    # Eliminar transcripción
    repo.delete(sample_transcription)

    # Verificar que ya no existe
    assert repo.exists(transcription_id) is False


# ==================== TEST MÉTODOS ESPECÍFICOS ====================


def test_get_by_video_id_success(db_session, sample_transcription):
    """
    Test que valida que get_by_video_id() encuentra transcripción por video_id.

    Verifica:
    - Encuentra la transcripción correcta por video_id
    - Retorna la instancia completa de Transcription
    """
    repo = TranscriptionRepository(db_session)

    found = repo.get_by_video_id(sample_transcription.video_id)

    assert found is not None
    assert found.id == sample_transcription.id
    assert found.video_id == sample_transcription.video_id
    assert found.text == sample_transcription.text
    assert found.language == "en"


def test_get_by_video_id_not_found(db_session, sample_video):
    """
    Test que valida que get_by_video_id() retorna None si video sin transcripción.

    Verifica:
    - Retorna None cuando el video no tiene transcripción
    """
    repo = TranscriptionRepository(db_session)

    # sample_video no tiene transcripción todavía (solo sample_transcription tiene)
    # Crear un video nuevo sin transcripción
    from src.models import Video, VideoStatus
    from datetime import datetime, timezone

    video_without_transcription = Video(
        source_id=sample_video.source_id,
        youtube_id="no_transcription_123",
        title="Video without transcription",
        url="https://youtube.com/watch?v=no_trans",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video_without_transcription)
    db_session.commit()

    found = repo.get_by_video_id(video_without_transcription.id)

    assert found is None


def test_exists_by_video_id_true(db_session, sample_transcription):
    """
    Test que valida que exists_by_video_id() retorna True si existe transcripción.

    Verifica:
    - Retorna True cuando el video tiene transcripción
    """
    repo = TranscriptionRepository(db_session)

    exists = repo.exists_by_video_id(sample_transcription.video_id)

    assert exists is True


def test_exists_by_video_id_false(db_session, sample_video):
    """
    Test que valida que exists_by_video_id() retorna False si no existe.

    Verifica:
    - Retorna False cuando el video no tiene transcripción
    """
    repo = TranscriptionRepository(db_session)

    # Crear video nuevo sin transcripción
    from src.models import Video, VideoStatus
    from datetime import datetime, timezone

    video_without_transcription = Video(
        source_id=sample_video.source_id,
        youtube_id="no_exists_123",
        title="Video without transcription",
        url="https://youtube.com/watch?v=no_exists",
        duration_seconds=200,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video_without_transcription)
    db_session.commit()

    exists = repo.exists_by_video_id(video_without_transcription.id)

    assert exists is False


def test_get_by_language_filters_correctly(db_session, sample_video, transcription_factory):
    """
    Test que valida que get_by_language() filtra por idioma correctamente.

    Verifica:
    - Filtra solo las transcripciones del idioma especificado
    - Retorna lista vacía si no hay transcripciones en ese idioma
    - Funciona con múltiples idiomas
    """
    repo = TranscriptionRepository(db_session)

    # Crear múltiples videos con diferentes idiomas
    from src.models import Video, VideoStatus
    from datetime import datetime, timezone

    video_es = Video(
        source_id=sample_video.source_id,
        youtube_id="spanish_video",
        title="Video en español",
        url="https://youtube.com/watch?v=es",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    video_en = Video(
        source_id=sample_video.source_id,
        youtube_id="english_video",
        title="English video",
        url="https://youtube.com/watch?v=en",
        duration_seconds=400,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    video_fr = Video(
        source_id=sample_video.source_id,
        youtube_id="french_video",
        title="Vidéo française",
        url="https://youtube.com/watch?v=fr",
        duration_seconds=500,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add_all([video_es, video_en, video_fr])
    db_session.commit()

    # Crear transcripciones en diferentes idiomas
    trans_es_1 = transcription_factory(
        video_id=video_es.id, language="es", text="Transcripción en español uno"
    )
    trans_es_2 = transcription_factory(
        video_id=sample_video.id, language="es", text="Transcripción en español dos"
    )
    trans_en = transcription_factory(video_id=video_en.id, language="en", text="English transcription")
    trans_fr = transcription_factory(video_id=video_fr.id, language="fr", text="Transcription française")

    # Buscar por idioma español
    spanish_transcriptions = repo.get_by_language("es")
    assert len(spanish_transcriptions) == 2
    assert all(t.language == "es" for t in spanish_transcriptions)
    assert set(t.id for t in spanish_transcriptions) == {trans_es_1.id, trans_es_2.id}

    # Buscar por idioma inglés
    english_transcriptions = repo.get_by_language("en")
    assert len(english_transcriptions) == 1
    assert english_transcriptions[0].id == trans_en.id

    # Buscar por idioma francés
    french_transcriptions = repo.get_by_language("fr")
    assert len(french_transcriptions) == 1
    assert french_transcriptions[0].id == trans_fr.id

    # Buscar por idioma inexistente
    german_transcriptions = repo.get_by_language("de")
    assert len(german_transcriptions) == 0


# ==================== TEST CONSTRAINT UNIQUE ====================


def test_unique_constraint_video_id(db_session, sample_video, transcription_factory):
    """
    Test que valida el constraint UNIQUE en video_id (relación 1:1).

    Verifica:
    - No se pueden crear 2 transcripciones para el mismo video
    - Lanza IntegrityError al intentar duplicar video_id
    """
    repo = TranscriptionRepository(db_session)

    # Crear primera transcripción
    trans1 = transcription_factory(
        video_id=sample_video.id, language="en", text="First transcription"
    )

    # Intentar crear segunda transcripción para el mismo video
    with pytest.raises(IntegrityError) as exc_info:
        transcription_factory(
            video_id=sample_video.id,  # Mismo video_id
            language="es",
            text="Second transcription (should fail)",
        )

    # Verificar que el error es por UNIQUE constraint
    assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


# ==================== TEST RELACIÓN CON VIDEO ====================


def test_relationship_with_video(db_session, sample_transcription):
    """
    Test que valida la relación Transcription → Video (foreign key).

    Verifica:
    - La relación video carga correctamente (lazy='joined')
    - Se puede acceder a video.title desde transcription.video
    """
    repo = TranscriptionRepository(db_session)

    transcription = repo.get_by_id(sample_transcription.id)

    # Verificar que la relación funciona
    assert transcription.video is not None
    assert transcription.video.id == sample_transcription.video_id
    assert transcription.video.title == "Test Video"  # De sample_video en conftest


def test_cascade_delete_video_deletes_transcription(db_session, sample_video, transcription_factory):
    """
    Test que valida que eliminar Video elimina su Transcription (CASCADE).

    Verifica:
    - Al borrar un video, su transcripción también se borra (ON DELETE CASCADE)
    """
    repo = TranscriptionRepository(db_session)

    # Crear transcripción
    trans = transcription_factory(
        video_id=sample_video.id, language="en", text="Transcription to be deleted"
    )
    trans_id = trans.id

    # Eliminar el video
    db_session.delete(sample_video)
    db_session.commit()

    # Verificar que la transcripción también se eliminó
    assert repo.exists(trans_id) is False


# ==================== TEST CAMPO JSONB SEGMENTS ====================


def test_segments_field_accepts_none(db_session, sample_video, transcription_factory):
    """
    Test que valida que segments puede ser None.

    Verifica:
    - Campo JSONB segments acepta None sin error
    """
    trans = transcription_factory(
        video_id=sample_video.id, language="en", text="Transcription without segments", segments=None
    )

    assert trans.segments is None
    assert trans.has_segments is False  # Property del modelo


def test_segments_field_accepts_complex_dict(db_session, sample_video, transcription_factory):
    """
    Test que valida que segments acepta dict complejo con timestamps.

    Verifica:
    - Campo JSONB segments acepta diccionarios complejos
    - Se serializa y deserializa correctamente
    """
    segments_data = {
        "segments": [
            {"start": 0.0, "end": 5.2, "text": "Hello, welcome to this tutorial."},
            {"start": 5.2, "end": 10.8, "text": "Today we will learn about FastAPI."},
            {"start": 10.8, "end": 18.5, "text": "Let's start with the basics."},
        ]
    }

    trans = transcription_factory(
        video_id=sample_video.id,
        language="en",
        text="Transcription with segments",
        segments=segments_data,
    )

    # Verificar que se guardó correctamente
    assert trans.segments is not None
    assert trans.has_segments is True
    assert "segments" in trans.segments
    assert len(trans.segments["segments"]) == 3
    assert trans.segments["segments"][0]["start"] == 0.0
    assert trans.segments["segments"][0]["text"] == "Hello, welcome to this tutorial."


def test_segments_field_persists_and_retrieves_correctly(
    db_session, sample_video, transcription_factory
):
    """
    Test que valida que segments se persiste y recupera correctamente de BD.

    Verifica:
    - JSONB se serializa correctamente al guardar
    - JSONB se deserializa correctamente al leer
    """
    repo = TranscriptionRepository(db_session)

    segments_data = {
        "segments": [{"start": 0.0, "end": 3.5, "text": "Test segment"}],
        "metadata": {"total_duration": 3.5, "word_count": 2},
    }

    trans = transcription_factory(
        video_id=sample_video.id,
        language="en",
        text="Test",
        segments=segments_data,
    )

    # Recuperar de BD
    retrieved = repo.get_by_id(trans.id)

    assert retrieved.segments is not None
    assert retrieved.segments["segments"][0]["text"] == "Test segment"
    assert retrieved.segments["metadata"]["total_duration"] == 3.5
