"""
Tests de integración COMPLETOS para SummaryRepository.

Este es el repository MÁS COMPLEJO del sistema (usado por API + Bot).
Requiere cobertura exhaustiva de:
- Herencia correcta de BaseRepository (CRUD automático)
- Métodos específicos: get_by_transcription_id, get_recent, search_by_text,
  get_by_category, search_by_keyword
- Full-text search en PostgreSQL (índice GIN)
- Array search en keywords (operador ANY)
- Constraint UNIQUE en transcription_id (relación 1:1)
- Relación completa: Summary → Transcription → Video → Source
- Campos JSONB (extra_metadata)

NOTA: Los métodos get_unsent_to_telegram() y mark_as_sent() existen en el
repository pero NO están funcionales porque los campos sent_to_telegram,
sent_at y telegram_message_ids NO están implementados en el modelo actual.
Se requiere migración de BD para agregar estos campos.
"""

import time
from datetime import datetime, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from src.models import Summary, Transcription, Video, VideoStatus
from src.repositories.summary_repository import SummaryRepository


# ==================== TEST HERENCIA CRUD ====================


def test_create_summary_inherited(db_session, sample_transcription):
    """
    Test que valida que create() heredado de BaseRepository funciona.

    Verifica:
    - SummaryRepository hereda correctamente BaseRepository[Summary]
    - Método create() persiste el resumen en BD
    - Se asignan IDs y timestamps automáticamente
    - Campos se guardan correctamente
    """
    repo = SummaryRepository(db_session)

    summary_data = Summary(
        transcription_id=sample_transcription.id,
        summary_text="Este video explica FastAPI, un framework moderno de Python.",
        keywords=["fastapi", "python", "framework"],
        category="framework",
        model_used="deepseek-chat",
        tokens_used=800,
        input_tokens=650,
        output_tokens=150,
        processing_time_ms=1100,
    )

    created = repo.create(summary_data)

    # Validar que se creó correctamente
    assert created.id is not None
    assert created.transcription_id == sample_transcription.id
    assert created.summary_text == "Este video explica FastAPI, un framework moderno de Python."
    assert created.keywords == ["fastapi", "python", "framework"]
    assert created.category == "framework"
    assert created.model_used == "deepseek-chat"
    assert created.tokens_used == 800
    assert created.input_tokens == 650
    assert created.output_tokens == 150
    assert created.processing_time_ms == 1100
    assert created.created_at is not None
    assert created.updated_at is not None


def test_get_by_id_inherited(db_session, sample_summary):
    """
    Test que valida que get_by_id() de SummaryRepository funciona.

    Verifica:
    - Método get_by_id() encuentra el resumen por UUID
    - Devuelve None si no existe (sobreescrito de BaseRepository)
    """
    from uuid import uuid4

    repo = SummaryRepository(db_session)

    # Buscar resumen existente
    found = repo.get_by_id(sample_summary.id, use_cache=False)
    assert found is not None
    assert found.id == sample_summary.id
    assert found.transcription_id == sample_summary.transcription_id

    # Buscar resumen inexistente debe devolver None
    not_found = repo.get_by_id(uuid4(), use_cache=False)
    assert not_found is None


def test_delete_summary_inherited(db_session, sample_summary):
    """
    Test que valida que delete() heredado de BaseRepository funciona.

    Verifica:
    - Método delete() elimina el resumen de BD
    - No se puede encontrar después de eliminado (usando exists())
    """
    repo = SummaryRepository(db_session)

    summary_id = sample_summary.id

    # Eliminar resumen
    repo.delete(sample_summary)

    # Verificar que ya no existe
    assert repo.exists(summary_id) is False


# ==================== TEST MÉTODOS ESPECÍFICOS ====================


def test_get_by_transcription_id_success(db_session, sample_summary):
    """
    Test que valida que get_by_transcription_id() encuentra resumen.

    Verifica:
    - Encuentra el resumen correcto por transcription_id
    - Retorna la instancia completa de Summary
    """
    repo = SummaryRepository(db_session)

    found = repo.get_by_transcription_id(sample_summary.transcription_id)

    assert found is not None
    assert found.id == sample_summary.id
    assert found.transcription_id == sample_summary.transcription_id
    assert found.summary_text == sample_summary.summary_text
    assert found.category == "framework"


def test_get_by_transcription_id_not_found(db_session, sample_transcription):
    """
    Test que valida que get_by_transcription_id() retorna None si no hay resumen.

    Verifica:
    - Retorna None cuando la transcripción no tiene resumen
    """
    repo = SummaryRepository(db_session)

    # Crear transcripción nueva sin resumen
    from src.models import Video

    video_without_summary = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="no_summary_123",
        title="Video without summary",
        url="https://youtube.com/watch?v=no_sum",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video_without_summary)
    db_session.commit()

    transcription_without_summary = Transcription(
        video_id=video_without_summary.id,
        text="Transcription without summary",
        language="en",
        model_used="whisper-base",
        duration_seconds=300,
    )
    db_session.add(transcription_without_summary)
    db_session.commit()

    found = repo.get_by_transcription_id(transcription_without_summary.id)

    assert found is None


def test_get_recent_returns_ordered_by_created_at_desc(
    db_session, sample_transcription, transcription_factory, summary_factory
):
    """
    Test que valida que get_recent() retorna resúmenes ordenados DESC.

    Verifica:
    - Retorna resúmenes ordenados por created_at descendente (más recientes primero)
    - Respeta el parámetro limit
    """
    repo = SummaryRepository(db_session)

    # Crear múltiples transcripciones y resúmenes con delays para timestamps diferentes
    from src.models import Video

    summaries_created = []

    for i in range(5):
        video = Video(
            source_id=sample_transcription.video.source_id,
            youtube_id=f"recent_test_{i}",
            title=f"Video {i}",
            url=f"https://youtube.com/watch?v=recent_{i}",
            duration_seconds=300,
            status=VideoStatus.PENDING,
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(video)
        db_session.commit()

        trans = transcription_factory(
            video_id=video.id,
            text=f"Transcription {i}",
            language="en",
        )

        # Delay mayor para asegurar timestamps diferentes en PostgreSQL
        time.sleep(0.1)

        summary = summary_factory(
            transcription_id=trans.id,
            summary_text=f"Summary {i}",
            category="concept",
        )
        summaries_created.append(summary)

    # Obtener 3 más recientes
    recent = repo.get_recent(limit=3)

    assert len(recent) == 3

    # Verificar que están ordenados por created_at descendente
    # (no podemos asumir IDs específicos porque sample_summary también existe)
    for i in range(len(recent) - 1):
        assert recent[i].created_at >= recent[i + 1].created_at


def test_get_recent_respects_limit(
    db_session, sample_transcription, transcription_factory, summary_factory
):
    """
    Test que valida que get_recent() respeta el parámetro limit.

    Verifica:
    - Con limit=5, retorna máximo 5 resultados
    - Con limit=10 (default), retorna máximo 10 resultados
    """
    repo = SummaryRepository(db_session)

    # Crear 12 resúmenes
    from src.models import Video

    for i in range(12):
        video = Video(
            source_id=sample_transcription.video.source_id,
            youtube_id=f"limit_test_{i}",
            title=f"Video {i}",
            url=f"https://youtube.com/watch?v=limit_{i}",
            duration_seconds=300,
            status=VideoStatus.PENDING,
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(video)
        db_session.commit()

        trans = transcription_factory(
            video_id=video.id,
            text=f"Transcription {i}",
            language="en",
        )

        summary_factory(
            transcription_id=trans.id,
            summary_text=f"Summary {i}",
            category="concept",
        )

    # Probar limit=5
    recent_5 = repo.get_recent(limit=5)
    assert len(recent_5) == 5

    # Probar limit=10 (default)
    recent_10 = repo.get_recent(limit=10)
    assert len(recent_10) == 10

    # Probar limit=100 (más que los existentes)
    recent_all = repo.get_recent(limit=100)
    # Nota: No podemos asumir cantidad exacta porque otros tests
    # pueden haber creado summaries en la misma sesión de BD
    assert len(recent_all) >= 12  # Al menos los 12 que acabamos de crear


def test_search_by_text_full_text_search(
    db_session, sample_transcription, transcription_factory, summary_factory
):
    """
    Test que valida búsqueda full-text en PostgreSQL.

    Verifica:
    - search_by_text() usa índice GIN para búsqueda eficiente
    - Encuentra resúmenes que contienen el texto buscado
    - No encuentra resúmenes que no contienen el texto
    - Funciona con búsquedas multi-palabra
    """
    repo = SummaryRepository(db_session)

    # Crear transcripciones y resúmenes con textos específicos
    from src.models import Video

    # Resumen 1: FastAPI
    video1 = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="search_fastapi",
        title="FastAPI tutorial",
        url="https://youtube.com/watch?v=fastapi",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video1)
    db_session.commit()

    trans1 = transcription_factory(video_id=video1.id, text="FastAPI content", language="es")
    sum1 = summary_factory(
        transcription_id=trans1.id,
        summary_text="FastAPI es un framework web moderno para Python que permite crear APIs REST de forma rápida.",
        category="framework",
        keywords=["fastapi", "python"],
    )

    # Resumen 2: Python async
    video2 = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="search_async",
        title="Python async",
        url="https://youtube.com/watch?v=async",
        duration_seconds=400,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video2)
    db_session.commit()

    trans2 = transcription_factory(video_id=video2.id, text="Async content", language="es")
    sum2 = summary_factory(
        transcription_id=trans2.id,
        summary_text="Python async programming permite ejecutar código asíncrono usando await y async/await.",
        category="language",
        keywords=["python", "async"],
    )

    # Resumen 3: Docker containers
    video3 = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="search_docker",
        title="Docker guide",
        url="https://youtube.com/watch?v=docker",
        duration_seconds=500,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video3)
    db_session.commit()

    trans3 = transcription_factory(video_id=video3.id, text="Docker content", language="es")
    sum3 = summary_factory(
        transcription_id=trans3.id,
        summary_text="Docker containers permiten empaquetar aplicaciones con sus dependencias de forma portable.",
        category="tool",
        keywords=["docker", "containers"],
    )

    # Búsqueda 1: "FastAPI" debe encontrar sum1
    results_fastapi = repo.search_by_text("FastAPI")
    assert len(results_fastapi) >= 1
    assert any(s.id == sum1.id for s in results_fastapi)

    # Búsqueda 2: "Python async" debe encontrar sum2
    results_async = repo.search_by_text("Python async")
    assert len(results_async) >= 1
    assert any(s.id == sum2.id for s in results_async)

    # Búsqueda 3: "Docker containers" debe encontrar sum3
    results_docker = repo.search_by_text("Docker containers")
    assert len(results_docker) >= 1
    assert any(s.id == sum3.id for s in results_docker)

    # Búsqueda 4: "Kubernetes" NO debe encontrar nada
    results_k8s = repo.search_by_text("Kubernetes")
    assert len(results_k8s) == 0


def test_search_by_text_respects_limit(
    db_session, sample_transcription, transcription_factory, summary_factory
):
    """
    Test que valida que search_by_text() respeta el parámetro limit.

    Verifica:
    - Con limit=5, retorna máximo 5 resultados
    """
    repo = SummaryRepository(db_session)

    # Crear 10 resúmenes que contienen "Python"
    from src.models import Video

    for i in range(10):
        video = Video(
            source_id=sample_transcription.video.source_id,
            youtube_id=f"search_limit_{i}",
            title=f"Python video {i}",
            url=f"https://youtube.com/watch?v=search_limit_{i}",
            duration_seconds=300,
            status=VideoStatus.PENDING,
            published_at=datetime.now(timezone.utc),
        )
        db_session.add(video)
        db_session.commit()

        trans = transcription_factory(video_id=video.id, text=f"Python content {i}", language="es")
        summary_factory(
            transcription_id=trans.id,
            summary_text=f"Este video habla sobre Python y sus características {i}",
            category="language",
        )

    # Buscar con limit=5
    results = repo.search_by_text("Python", limit=5)
    assert len(results) == 5


def test_get_by_category_filters_correctly(
    db_session, sample_transcription, transcription_factory, summary_factory
):
    """
    Test que valida que get_by_category() filtra por categoría.

    Verifica:
    - Filtra solo los resúmenes de la categoría especificada
    - Funciona con "framework", "language", "tool", "concept"
    - Retorna lista vacía si no hay resúmenes en esa categoría
    """
    repo = SummaryRepository(db_session)

    # Crear resúmenes de diferentes categorías
    from src.models import Video

    # Category: framework
    video_fw = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="cat_framework",
        title="Framework video",
        url="https://youtube.com/watch?v=fw",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video_fw)
    db_session.commit()

    trans_fw = transcription_factory(video_id=video_fw.id, text="Framework content", language="es")
    sum_fw = summary_factory(
        transcription_id=trans_fw.id,
        summary_text="Framework summary",
        category="framework",
        keywords=["fastapi"],
    )

    # Category: language
    video_lang = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="cat_language",
        title="Language video",
        url="https://youtube.com/watch?v=lang",
        duration_seconds=400,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video_lang)
    db_session.commit()

    trans_lang = transcription_factory(
        video_id=video_lang.id, text="Language content", language="es"
    )
    sum_lang = summary_factory(
        transcription_id=trans_lang.id,
        summary_text="Language summary",
        category="language",
        keywords=["python"],
    )

    # Category: tool
    video_tool = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="cat_tool",
        title="Tool video",
        url="https://youtube.com/watch?v=tool",
        duration_seconds=500,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video_tool)
    db_session.commit()

    trans_tool = transcription_factory(video_id=video_tool.id, text="Tool content", language="es")
    sum_tool = summary_factory(
        transcription_id=trans_tool.id,
        summary_text="Tool summary",
        category="tool",
        keywords=["docker"],
    )

    # Filtrar por "framework"
    frameworks = repo.get_by_category("framework")
    assert len(frameworks) >= 1
    assert any(s.id == sum_fw.id for s in frameworks)
    assert all(s.category == "framework" for s in frameworks)

    # Filtrar por "language"
    languages = repo.get_by_category("language")
    assert len(languages) >= 1
    assert any(s.id == sum_lang.id for s in languages)
    assert all(s.category == "language" for s in languages)

    # Filtrar por "tool"
    tools = repo.get_by_category("tool")
    assert len(tools) >= 1
    assert any(s.id == sum_tool.id for s in tools)
    assert all(s.category == "tool" for s in tools)

    # Filtrar por categoría inexistente
    nonexistent = repo.get_by_category("nonexistent_category")
    assert len(nonexistent) == 0


def test_search_by_keyword_array_search(
    db_session, sample_transcription, transcription_factory, summary_factory
):
    """
    Test que valida búsqueda en array keywords usando operador ANY.

    Verifica:
    - search_by_keyword() busca en el array de keywords
    - Encuentra resúmenes que contienen el keyword específico
    - No encuentra resúmenes que no contienen el keyword
    - Funciona con múltiples resúmenes que comparten keywords
    """
    repo = SummaryRepository(db_session)

    # Crear resúmenes con diferentes keywords
    from src.models import Video

    # Summary 1: ["fastapi", "python"]
    video1 = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="kw_fastapi",
        title="FastAPI video",
        url="https://youtube.com/watch?v=kw_fastapi",
        duration_seconds=300,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video1)
    db_session.commit()

    trans1 = transcription_factory(video_id=video1.id, text="FastAPI content", language="es")
    sum1 = summary_factory(
        transcription_id=trans1.id,
        summary_text="FastAPI summary",
        category="framework",
        keywords=["fastapi", "python"],
    )

    # Summary 2: ["docker", "containers"]
    video2 = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="kw_docker",
        title="Docker video",
        url="https://youtube.com/watch?v=kw_docker",
        duration_seconds=400,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video2)
    db_session.commit()

    trans2 = transcription_factory(video_id=video2.id, text="Docker content", language="es")
    sum2 = summary_factory(
        transcription_id=trans2.id,
        summary_text="Docker summary",
        category="tool",
        keywords=["docker", "containers"],
    )

    # Summary 3: ["async", "python"]
    video3 = Video(
        source_id=sample_transcription.video.source_id,
        youtube_id="kw_async",
        title="Async video",
        url="https://youtube.com/watch?v=kw_async",
        duration_seconds=500,
        status=VideoStatus.PENDING,
        published_at=datetime.now(timezone.utc),
    )
    db_session.add(video3)
    db_session.commit()

    trans3 = transcription_factory(video_id=video3.id, text="Async content", language="es")
    sum3 = summary_factory(
        transcription_id=trans3.id,
        summary_text="Async summary",
        category="language",
        keywords=["async", "python"],
    )

    # Buscar keyword "python" debe encontrar sum1 y sum3
    results_python = repo.search_by_keyword("python")
    assert len(results_python) >= 2
    python_ids = {s.id for s in results_python}
    assert sum1.id in python_ids
    assert sum3.id in python_ids

    # Buscar keyword "docker" debe encontrar solo sum2
    results_docker = repo.search_by_keyword("docker")
    assert len(results_docker) >= 1
    assert any(s.id == sum2.id for s in results_docker)

    # Buscar keyword "containers" debe encontrar solo sum2
    results_containers = repo.search_by_keyword("containers")
    assert len(results_containers) >= 1
    assert any(s.id == sum2.id for s in results_containers)

    # Buscar keyword inexistente
    results_none = repo.search_by_keyword("nonexistent_keyword")
    assert len(results_none) == 0


# ==================== TEST CONSTRAINT UNIQUE ====================


def test_unique_constraint_transcription_id(db_session, sample_transcription, summary_factory):
    """
    Test que valida el constraint UNIQUE en transcription_id (relación 1:1).

    Verifica:
    - No se pueden crear 2 resúmenes para la misma transcripción
    - Lanza IntegrityError al intentar duplicar transcription_id
    """
    # Crear primer resumen
    sum1 = summary_factory(
        transcription_id=sample_transcription.id,
        summary_text="First summary",
        category="concept",
    )

    # Intentar crear segundo resumen para la misma transcripción
    with pytest.raises(IntegrityError) as exc_info:
        summary_factory(
            transcription_id=sample_transcription.id,  # Mismo transcription_id
            summary_text="Second summary (should fail)",
            category="concept",
        )

    # Verificar que el error es por UNIQUE constraint
    assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


# ==================== TEST RELACIONES EN CADENA ====================


def test_relationship_summary_to_transcription(db_session, sample_summary):
    """
    Test que valida la relación Summary → Transcription.

    Verifica:
    - La relación transcription carga correctamente (lazy='joined')
    - Se puede acceder a transcription.text desde summary.transcription
    """
    repo = SummaryRepository(db_session)

    summary = repo.get_by_id(sample_summary.id)

    # Verificar relación Summary → Transcription
    assert summary.transcription is not None
    assert summary.transcription.id == sample_summary.transcription_id
    assert summary.transcription.text is not None


def test_relationship_chain_summary_to_video_to_source(db_session, sample_summary):
    """
    Test que valida la cadena completa de relaciones:
    Summary → Transcription → Video → Source.

    Verifica:
    - Se puede navegar por toda la cadena de relaciones
    - summary.transcription.video.source es accesible
    """
    repo = SummaryRepository(db_session)

    summary = repo.get_by_id(sample_summary.id)

    # Verificar cadena Summary → Transcription → Video → Source
    assert summary.transcription is not None
    assert summary.transcription.video is not None
    assert summary.transcription.video.source is not None

    # Verificar datos del video
    assert summary.transcription.video.title == "Test Video"

    # Verificar datos del source
    assert summary.transcription.video.source.name == "Test Channel"


def test_cascade_delete_transcription_deletes_summary(
    db_session, sample_transcription, summary_factory
):
    """
    Test que valida que eliminar Transcription elimina su Summary (CASCADE).

    Verifica:
    - Al borrar una transcripción, su resumen también se borra (ON DELETE CASCADE)
    """
    repo = SummaryRepository(db_session)

    # Crear resumen
    summary = summary_factory(
        transcription_id=sample_transcription.id,
        summary_text="Summary to be deleted",
        category="concept",
    )
    summary_id = summary.id

    # Eliminar la transcripción
    db_session.delete(sample_transcription)
    db_session.commit()

    # Verificar que el resumen también se eliminó
    assert repo.exists(summary_id) is False


# ==================== TEST CAMPO JSONB ====================


def test_extra_metadata_field_accepts_none(db_session, sample_transcription, summary_factory):
    """
    Test que valida que extra_metadata puede ser None.

    Verifica:
    - Campo JSONB extra_metadata acepta None sin error
    """
    summary = summary_factory(
        transcription_id=sample_transcription.id,
        summary_text="Summary without metadata",
        category="concept",
        extra_metadata=None,
    )

    assert summary.extra_metadata is None


def test_extra_metadata_field_accepts_complex_dict(
    db_session, sample_transcription, summary_factory
):
    """
    Test que valida que extra_metadata acepta dict complejo.

    Verifica:
    - Campo JSONB extra_metadata acepta diccionarios complejos
    - Se serializa y deserializa correctamente
    """
    metadata = {
        "temperature": 0.7,
        "max_tokens": 500,
        "prompt_version": "v2.1",
        "custom_settings": {"format": "markdown", "include_timestamps": True},
    }

    summary = summary_factory(
        transcription_id=sample_transcription.id,
        summary_text="Summary with complex metadata",
        category="concept",
        extra_metadata=metadata,
    )

    # Verificar que se guardó correctamente
    assert summary.extra_metadata is not None
    assert summary.extra_metadata["temperature"] == 0.7
    assert summary.extra_metadata["max_tokens"] == 500
    assert summary.extra_metadata["prompt_version"] == "v2.1"
    assert summary.extra_metadata["custom_settings"]["format"] == "markdown"


def test_extra_metadata_persists_and_retrieves_correctly(
    db_session, sample_transcription, summary_factory
):
    """
    Test que valida que extra_metadata se persiste y recupera de BD.

    Verifica:
    - JSONB se serializa correctamente al guardar
    - JSONB se deserializa correctamente al leer
    """
    repo = SummaryRepository(db_session)

    metadata = {
        "model_config": {"temperature": 0.8, "top_p": 0.9},
        "retry_count": 2,
    }

    summary = summary_factory(
        transcription_id=sample_transcription.id,
        summary_text="Test metadata persistence",
        category="concept",
        extra_metadata=metadata,
    )

    # Recuperar de BD
    retrieved = repo.get_by_id(summary.id)

    assert retrieved.extra_metadata is not None
    assert retrieved.extra_metadata["model_config"]["temperature"] == 0.8
    assert retrieved.extra_metadata["retry_count"] == 2


# ==================== TEST PROPIEDADES DEL MODELO ====================


def test_model_properties(db_session, sample_summary):
    """
    Test que valida las propiedades calculadas del modelo Summary.

    Verifica:
    - word_count calcula correctamente
    - has_keywords retorna True/False correctamente
    - compression_ratio calcula correctamente
    - estimated_cost_usd calcula correctamente
    """
    # word_count
    assert sample_summary.word_count > 0

    # has_keywords
    assert sample_summary.has_keywords is True

    # compression_ratio
    assert sample_summary.compression_ratio is not None
    assert 0.0 < sample_summary.compression_ratio < 1.0

    # estimated_cost_usd
    assert sample_summary.estimated_cost_usd is not None
    assert sample_summary.estimated_cost_usd > 0.0


def test_model_to_dict(db_session, sample_summary):
    """
    Test que valida el método to_dict() del modelo Summary.

    Verifica:
    - to_dict() retorna diccionario con todas las claves esperadas
    - Los valores son correctos y serializables a JSON
    """
    summary_dict = sample_summary.to_dict()

    assert "id" in summary_dict
    assert "transcription_id" in summary_dict
    assert "summary_text" in summary_dict
    assert "keywords" in summary_dict
    assert "category" in summary_dict
    assert "model_used" in summary_dict
    assert "tokens_used" in summary_dict
    assert "created_at" in summary_dict
    assert "updated_at" in summary_dict

    # Verificar tipos
    assert isinstance(summary_dict["id"], str)
    assert isinstance(summary_dict["keywords"], list)
    assert isinstance(summary_dict["extra_metadata"], dict)
