"""
Tests de integración EXHAUSTIVOS para TelegramUserRepository.

Este es el ÚLTIMO repository del sistema. Requiere cobertura exhaustiva de:
- Herencia correcta de BaseRepository (CRUD automático)
- Métodos específicos: get_by_telegram_id, exists_by_telegram_id,
  subscribe_to_source, unsubscribe_from_source, get_user_subscriptions,
  get_source_subscribers, is_subscribed
- Relación M:N completa con Source a través de user_source_subscriptions
- Constraint UNIQUE en (user_id, source_id) en tabla intermedia
- Casos edge: 0 suscripciones, múltiples suscripciones, etc.
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models import TelegramUser
from src.repositories.exceptions import AlreadyExistsError, NotFoundError
from src.repositories.telegram_user_repository import TelegramUserRepository

# ==================== TEST HERENCIA CRUD ====================


def test_create_telegram_user_inherited(db_session):
    """
    Test que valida que create() heredado de BaseRepository funciona.

    Verifica:
    - TelegramUserRepository hereda correctamente BaseRepository[TelegramUser]
    - Método create() persiste el usuario en BD
    - Se asignan IDs y timestamps automáticamente
    - Campos se guardan correctamente
    """
    repo = TelegramUserRepository(db_session)

    user_data = TelegramUser(
        telegram_id=987654321,
        username="john_doe",
        first_name="John",
        last_name="Doe",
        is_active=True,
        language_code="en",
    )

    created = repo.create(user_data)

    # Validar que se creó correctamente
    assert created.id is not None
    assert created.telegram_id == 987654321
    assert created.username == "john_doe"
    assert created.first_name == "John"
    assert created.last_name == "Doe"
    assert created.is_active is True
    assert created.language_code == "en"
    assert created.created_at is not None
    assert created.updated_at is not None


def test_get_by_id_inherited(db_session, sample_telegram_user):
    """
    Test que valida que get_by_id() heredado de BaseRepository funciona.

    Verifica:
    - Método get_by_id() encuentra el usuario por UUID
    - Lanza NotFoundError si no existe
    """
    from uuid import uuid4

    repo = TelegramUserRepository(db_session)

    # Buscar usuario existente
    found = repo.get_by_id(sample_telegram_user.id)
    assert found is not None
    assert found.id == sample_telegram_user.id
    assert found.telegram_id == sample_telegram_user.telegram_id

    # Buscar usuario inexistente debe lanzar NotFoundError
    with pytest.raises(NotFoundError) as exc_info:
        repo.get_by_id(uuid4())

    assert "TelegramUser" in str(exc_info.value)


def test_delete_telegram_user_inherited(db_session, sample_telegram_user):
    """
    Test que valida que delete() heredado de BaseRepository funciona.

    Verifica:
    - Método delete() elimina el usuario de BD
    - No se puede encontrar después de eliminado (usando exists())
    """
    repo = TelegramUserRepository(db_session)

    user_id = sample_telegram_user.id

    # Eliminar usuario
    repo.delete(sample_telegram_user)

    # Verificar que ya no existe
    assert repo.exists(user_id) is False


# ==================== TEST MÉTODOS ESPECÍFICOS ====================


def test_get_by_telegram_id_success(db_session, sample_telegram_user):
    """
    Test que valida que get_by_telegram_id() encuentra usuario por telegram_id.

    Verifica:
    - Encuentra el usuario correcto por telegram_id (bigint)
    - Retorna la instancia completa de TelegramUser
    """
    repo = TelegramUserRepository(db_session)

    found = repo.get_by_telegram_id(sample_telegram_user.telegram_id)

    assert found is not None
    assert found.id == sample_telegram_user.id
    assert found.telegram_id == sample_telegram_user.telegram_id
    assert found.username == sample_telegram_user.username


def test_get_by_telegram_id_not_found(db_session):
    """
    Test que valida que get_by_telegram_id() retorna None si no existe.

    Verifica:
    - Retorna None cuando el telegram_id no existe
    """
    repo = TelegramUserRepository(db_session)

    found = repo.get_by_telegram_id(999999999)

    assert found is None


def test_exists_by_telegram_id_true(db_session, sample_telegram_user):
    """
    Test que valida que exists_by_telegram_id() retorna True si existe.

    Verifica:
    - Retorna True cuando el telegram_id existe
    """
    repo = TelegramUserRepository(db_session)

    exists = repo.exists_by_telegram_id(sample_telegram_user.telegram_id)

    assert exists is True


def test_exists_by_telegram_id_false(db_session):
    """
    Test que valida que exists_by_telegram_id() retorna False si no existe.

    Verifica:
    - Retorna False cuando el telegram_id no existe
    """
    repo = TelegramUserRepository(db_session)

    exists = repo.exists_by_telegram_id(888888888)

    assert exists is False


def test_unique_constraint_telegram_id(db_session, telegram_user_factory):
    """
    Test que valida el constraint UNIQUE en telegram_id.

    Verifica:
    - No se pueden crear 2 usuarios con el mismo telegram_id
    - Lanza IntegrityError al intentar duplicar telegram_id
    """
    # Crear primer usuario
    telegram_user_factory(telegram_id=111111111, username="user1")

    # Intentar crear segundo usuario con mismo telegram_id
    with pytest.raises(IntegrityError) as exc_info:
        telegram_user_factory(
            telegram_id=111111111,  # Mismo telegram_id
            username="user2",
        )

    # Verificar que el error es por UNIQUE constraint
    assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


# ==================== TEST SUSCRIPCIONES M:N ====================


def test_subscribe_to_source_creates_subscription(db_session, sample_telegram_user, sample_source):
    """
    Test que valida que subscribe_to_source() crea entrada en tabla intermedia.

    Verifica:
    - Crea entrada en user_source_subscriptions
    - user.sources contiene la source
    - source.users contiene el user
    """
    repo = TelegramUserRepository(db_session)

    # Suscribir usuario a source
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    # Refrescar desde BD
    db_session.refresh(sample_telegram_user)
    db_session.refresh(sample_source)

    # Verificar relación M:N
    assert sample_source in sample_telegram_user.sources
    assert sample_telegram_user in sample_source.users


def test_subscribe_to_source_raises_already_exists_if_duplicate(
    db_session, sample_telegram_user, sample_source
):
    """
    Test que valida que subscribe_to_source() lanza AlreadyExistsError si ya suscrito.

    Verifica:
    - No permite suscripciones duplicadas
    - Lanza AlreadyExistsError con mensaje descriptivo
    """
    repo = TelegramUserRepository(db_session)

    # Primera suscripción (exitosa)
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    # Segunda suscripción (debe fallar)
    with pytest.raises(AlreadyExistsError) as exc_info:
        repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    assert "Subscription" in str(exc_info.value)


def test_subscribe_to_source_raises_not_found_if_source_not_exists(
    db_session, sample_telegram_user
):
    """
    Test que valida que subscribe_to_source() lanza NotFoundError si source no existe.

    Verifica:
    - Valida que la source existe antes de suscribir
    - Lanza NotFoundError con mensaje descriptivo
    """
    from uuid import uuid4

    repo = TelegramUserRepository(db_session)

    # Intentar suscribir a source inexistente
    with pytest.raises(NotFoundError) as exc_info:
        repo.subscribe_to_source(sample_telegram_user.id, uuid4())

    assert "Source" in str(exc_info.value)


def test_unsubscribe_from_source_removes_subscription(
    db_session, sample_telegram_user, sample_source
):
    """
    Test que valida que unsubscribe_from_source() elimina entrada de tabla intermedia.

    Verifica:
    - Elimina entrada de user_source_subscriptions
    - user.sources ya no contiene la source
    - source.users ya no contiene el user
    """
    repo = TelegramUserRepository(db_session)

    # Primero suscribir
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    # Ahora desuscribir
    repo.unsubscribe_from_source(sample_telegram_user.id, sample_source.id)

    # Refrescar desde BD
    db_session.refresh(sample_telegram_user)
    db_session.refresh(sample_source)

    # Verificar que ya no están relacionados
    assert sample_source not in sample_telegram_user.sources
    assert sample_telegram_user not in sample_source.users


def test_unsubscribe_from_source_raises_not_found_if_not_subscribed(
    db_session, sample_telegram_user, sample_source
):
    """
    Test que valida que unsubscribe_from_source() lanza NotFoundError si no está suscrito.

    Verifica:
    - No permite desuscribir si no hay suscripción
    - Lanza NotFoundError con mensaje descriptivo
    """
    repo = TelegramUserRepository(db_session)

    # Intentar desuscribir sin estar suscrito
    with pytest.raises(NotFoundError) as exc_info:
        repo.unsubscribe_from_source(sample_telegram_user.id, sample_source.id)

    assert "Subscription" in str(exc_info.value)


def test_get_user_subscriptions_returns_sources(
    db_session, sample_telegram_user, sample_source, source_factory
):
    """
    Test que valida que get_user_subscriptions() retorna lista de sources.

    Verifica:
    - Retorna lista vacía si no tiene suscripciones
    - Retorna todas las sources a las que está suscrito
    - Funciona con múltiples suscripciones
    """
    repo = TelegramUserRepository(db_session)

    # Sin suscripciones
    subscriptions = repo.get_user_subscriptions(sample_telegram_user.id)
    assert len(subscriptions) == 0

    # Crear más sources
    source2 = source_factory(
        name="Channel 2", url="https://youtube.com/@channel2", source_type="youtube"
    )
    source3 = source_factory(
        name="Channel 3", url="https://youtube.com/@channel3", source_type="youtube"
    )

    # Suscribir a múltiples sources
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)
    repo.subscribe_to_source(sample_telegram_user.id, source2.id)
    repo.subscribe_to_source(sample_telegram_user.id, source3.id)

    # Verificar suscripciones
    subscriptions = repo.get_user_subscriptions(sample_telegram_user.id)
    assert len(subscriptions) == 3

    subscription_ids = {s.id for s in subscriptions}
    assert sample_source.id in subscription_ids
    assert source2.id in subscription_ids
    assert source3.id in subscription_ids


def test_get_source_subscribers_returns_users(
    db_session, sample_source, sample_telegram_user, telegram_user_factory
):
    """
    Test que valida que get_source_subscribers() retorna lista de users.

    Verifica:
    - Retorna lista vacía si no tiene suscriptores
    - Retorna todos los users suscritos a la source
    - Funciona con múltiples suscriptores
    """
    repo = TelegramUserRepository(db_session)

    # Sin suscriptores
    subscribers = repo.get_source_subscribers(sample_source.id)
    assert len(subscribers) == 0

    # Crear más usuarios
    user2 = telegram_user_factory(telegram_id=222222222, username="user2", first_name="Jane")
    user3 = telegram_user_factory(telegram_id=333333333, username="user3", first_name="Bob")

    # Suscribir múltiples usuarios
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)
    repo.subscribe_to_source(user2.id, sample_source.id)
    repo.subscribe_to_source(user3.id, sample_source.id)

    # Verificar suscriptores
    subscribers = repo.get_source_subscribers(sample_source.id)
    assert len(subscribers) == 3

    subscriber_ids = {u.id for u in subscribers}
    assert sample_telegram_user.id in subscriber_ids
    assert user2.id in subscriber_ids
    assert user3.id in subscriber_ids


def test_get_source_subscribers_raises_not_found_if_source_not_exists(db_session):
    """
    Test que valida que get_source_subscribers() lanza NotFoundError si source no existe.

    Verifica:
    - Valida que la source existe
    - Lanza NotFoundError con mensaje descriptivo
    """
    from uuid import uuid4

    repo = TelegramUserRepository(db_session)

    # Intentar obtener suscriptores de source inexistente
    with pytest.raises(NotFoundError) as exc_info:
        repo.get_source_subscribers(uuid4())

    assert "Source" in str(exc_info.value)


def test_is_subscribed_returns_correct_state(
    db_session, sample_telegram_user, sample_source, source_factory
):
    """
    Test que valida que is_subscribed() retorna True/False según estado.

    Verifica:
    - Retorna False si no está suscrito
    - Retorna True si está suscrito
    - Funciona correctamente con múltiples sources
    """
    repo = TelegramUserRepository(db_session)

    # Crear otra source
    source2 = source_factory(
        name="Channel 2", url="https://youtube.com/@channel2", source_type="youtube"
    )

    # Inicialmente no suscrito
    assert repo.is_subscribed(sample_telegram_user.id, sample_source.id) is False
    assert repo.is_subscribed(sample_telegram_user.id, source2.id) is False

    # Suscribir a source1
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    # Verificar estados
    assert repo.is_subscribed(sample_telegram_user.id, sample_source.id) is True
    assert repo.is_subscribed(sample_telegram_user.id, source2.id) is False

    # Suscribir a source2
    repo.subscribe_to_source(sample_telegram_user.id, source2.id)

    # Ambos True
    assert repo.is_subscribed(sample_telegram_user.id, sample_source.id) is True
    assert repo.is_subscribed(sample_telegram_user.id, source2.id) is True

    # Desuscribir de source1
    repo.unsubscribe_from_source(sample_telegram_user.id, sample_source.id)

    # Verificar estados finales
    assert repo.is_subscribed(sample_telegram_user.id, sample_source.id) is False
    assert repo.is_subscribed(sample_telegram_user.id, source2.id) is True


def test_is_subscribed_returns_false_if_source_not_exists(db_session, sample_telegram_user):
    """
    Test que valida que is_subscribed() retorna False si source no existe.

    Verifica:
    - No lanza error, retorna False si source no existe
    """
    from uuid import uuid4

    repo = TelegramUserRepository(db_session)

    # Source inexistente
    result = repo.is_subscribed(sample_telegram_user.id, uuid4())

    assert result is False


# ==================== TEST RELACIÓN M:N COMPLETA ====================


def test_many_to_many_relationship_complete(db_session, telegram_user_factory, source_factory):
    """
    Test EXHAUSTIVO que valida la relación M:N completa.

    Verifica:
    - Múltiples usuarios pueden suscribirse a múltiples sources
    - user.sources retorna lista correcta
    - source.users retorna lista correcta
    - Tabla intermedia maneja correctamente la relación
    """
    repo = TelegramUserRepository(db_session)

    # Crear 3 usuarios
    user1 = telegram_user_factory(telegram_id=111111111, username="user1")
    user2 = telegram_user_factory(telegram_id=222222222, username="user2")
    user3 = telegram_user_factory(telegram_id=333333333, username="user3")

    # Crear 3 sources
    source1 = source_factory(name="Source 1", url="https://source1.com")
    source2 = source_factory(name="Source 2", url="https://source2.com")
    source3 = source_factory(name="Source 3", url="https://source3.com")

    # Suscribir:
    # user1 → [source1, source2]
    # user2 → [source1]
    # user3 → [source2, source3]
    repo.subscribe_to_source(user1.id, source1.id)
    repo.subscribe_to_source(user1.id, source2.id)

    repo.subscribe_to_source(user2.id, source1.id)

    repo.subscribe_to_source(user3.id, source2.id)
    repo.subscribe_to_source(user3.id, source3.id)

    # Verificar suscripciones de user1
    user1_sources = repo.get_user_subscriptions(user1.id)
    assert len(user1_sources) == 2
    user1_source_ids = {s.id for s in user1_sources}
    assert source1.id in user1_source_ids
    assert source2.id in user1_source_ids

    # Verificar suscripciones de user2
    user2_sources = repo.get_user_subscriptions(user2.id)
    assert len(user2_sources) == 1
    assert user2_sources[0].id == source1.id

    # Verificar suscripciones de user3
    user3_sources = repo.get_user_subscriptions(user3.id)
    assert len(user3_sources) == 2
    user3_source_ids = {s.id for s in user3_sources}
    assert source2.id in user3_source_ids
    assert source3.id in user3_source_ids

    # Verificar suscriptores de source1
    source1_subscribers = repo.get_source_subscribers(source1.id)
    assert len(source1_subscribers) == 2  # user1, user2
    source1_subscriber_ids = {u.id for u in source1_subscribers}
    assert user1.id in source1_subscriber_ids
    assert user2.id in source1_subscriber_ids

    # Verificar suscriptores de source2
    source2_subscribers = repo.get_source_subscribers(source2.id)
    assert len(source2_subscribers) == 2  # user1, user3
    source2_subscriber_ids = {u.id for u in source2_subscribers}
    assert user1.id in source2_subscriber_ids
    assert user3.id in source2_subscriber_ids

    # Verificar suscriptores de source3
    source3_subscribers = repo.get_source_subscribers(source3.id)
    assert len(source3_subscribers) == 1  # user3
    assert source3_subscribers[0].id == user3.id


def test_cascade_delete_user_removes_subscriptions(db_session, sample_telegram_user, sample_source):
    """
    Test que valida que eliminar usuario elimina sus suscripciones (CASCADE).

    Verifica:
    - Al borrar un usuario, sus entradas en user_source_subscriptions se borran
    - La source sigue existiendo
    """
    repo = TelegramUserRepository(db_session)

    # Suscribir usuario
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    # Verificar suscripción existe
    db_session.refresh(sample_source)
    assert len(sample_source.users) == 1

    # Eliminar usuario
    db_session.delete(sample_telegram_user)
    db_session.commit()

    # Verificar que source ya no tiene suscriptores
    db_session.refresh(sample_source)
    assert len(sample_source.users) == 0


def test_cascade_delete_source_removes_subscriptions(
    db_session, sample_telegram_user, sample_source
):
    """
    Test que valida que eliminar source elimina sus suscripciones (CASCADE).

    Verifica:
    - Al borrar una source, sus entradas en user_source_subscriptions se borran
    - El usuario sigue existiendo
    """
    repo = TelegramUserRepository(db_session)

    # Suscribir usuario
    repo.subscribe_to_source(sample_telegram_user.id, sample_source.id)

    # Verificar suscripción existe
    db_session.refresh(sample_telegram_user)
    assert len(sample_telegram_user.sources) == 1

    # Eliminar source
    db_session.delete(sample_source)
    db_session.commit()

    # Verificar que usuario ya no tiene suscripciones
    db_session.refresh(sample_telegram_user)
    assert len(sample_telegram_user.sources) == 0


# ==================== TEST PROPIEDADES DEL MODELO ====================


def test_model_properties(db_session, sample_telegram_user):
    """
    Test que valida las propiedades calculadas del modelo TelegramUser.

    Verifica:
    - full_name concatena first_name + last_name
    - display_name prioriza @username > full_name > telegram_id
    - subscription_count cuenta correctamente
    - has_subscriptions retorna True/False
    """
    # full_name
    assert sample_telegram_user.full_name == "Test User"

    # display_name (tiene username)
    assert sample_telegram_user.display_name == "@test_user"

    # subscription_count (sin suscripciones)
    assert sample_telegram_user.subscription_count == 0
    assert sample_telegram_user.has_subscriptions is False


def test_model_to_dict(db_session, sample_telegram_user):
    """
    Test que valida el método to_dict() del modelo TelegramUser.

    Verifica:
    - to_dict() retorna diccionario con todas las claves esperadas
    - Los valores son correctos y serializables a JSON
    """
    user_dict = sample_telegram_user.to_dict()

    assert "id" in user_dict
    assert "telegram_id" in user_dict
    assert "username" in user_dict
    assert "first_name" in user_dict
    assert "last_name" in user_dict
    assert "is_active" in user_dict
    assert "language_code" in user_dict
    assert "created_at" in user_dict
    assert "updated_at" in user_dict

    # Verificar tipos
    assert isinstance(user_dict["id"], str)
    assert isinstance(user_dict["telegram_id"], int)
    assert user_dict["telegram_id"] == 123456789
