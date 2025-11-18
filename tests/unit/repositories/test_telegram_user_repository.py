"""
Tests unitarios para TelegramUserRepository.

Cubre:
- CRUD básico (hereda de BaseRepository)
- Búsqueda por telegram_id (ID único de Telegram)
- Gestión de suscripciones many-to-many con Source
- Queries de usuarios activos/inactivos
- Validación de constraints únicos
- Gestión de estado bot_blocked

Requiere PostgreSQL en Docker: docker-compose up -d postgres
"""

import pytest
from uuid import uuid4
from sqlalchemy.exc import IntegrityError

from src.models.telegram_user import TelegramUser
from src.models.source import Source
from src.repositories.telegram_user_repository import TelegramUserRepository
from src.repositories.exceptions import NotFoundError, AlreadyExistsError


class TestTelegramUserRepositoryCRUD:
    """Tests para operaciones CRUD básicas (heredadas de BaseRepository)."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de TelegramUserRepository."""
        return TelegramUserRepository(db_session)

    def test_create_telegram_user(self, repository, db_session):
        """Test creación exitosa de usuario de Telegram."""
        # Arrange
        user = TelegramUser(
            telegram_id=999888777,
            username="testuser",
            first_name="Test",
            last_name="User",
            is_active=True,
            language_code="en"
        )

        # Act
        created = repository.create(user)

        # Assert
        assert created.id is not None
        assert created.telegram_id == 999888777
        assert created.username == "testuser"
        assert created.first_name == "Test"
        assert created.last_name == "User"
        assert created.is_active is True
        assert created.language_code == "en"
        assert created.bot_blocked is False  # Default
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_get_by_id_found(self, repository, sample_telegram_user):
        """Test búsqueda por UUID exitosa."""
        # Act
        found = repository.get_by_id(sample_telegram_user.id)

        # Assert
        assert found.id == sample_telegram_user.id
        assert found.telegram_id == sample_telegram_user.telegram_id

    def test_get_by_id_not_found(self, repository):
        """Test búsqueda de usuario inexistente lanza NotFoundError."""
        # Arrange
        fake_uuid = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            repository.get_by_id(fake_uuid)

        assert "TelegramUser" in str(exc_info.value)

    def test_update_telegram_user(self, repository, sample_telegram_user, db_session):
        """Test actualización exitosa de usuario."""
        # Arrange
        sample_telegram_user.username = "updated_user"
        sample_telegram_user.bot_blocked = True

        # Act
        updated = repository.update(sample_telegram_user)

        # Assert
        assert updated.id == sample_telegram_user.id
        assert updated.username == "updated_user"
        assert updated.bot_blocked is True

    def test_delete_telegram_user(self, repository, sample_telegram_user, db_session):
        """Test eliminación física de usuario."""
        # Arrange
        user_id = sample_telegram_user.id

        # Act
        repository.delete(sample_telegram_user)

        # Assert
        found = db_session.get(TelegramUser, user_id)
        assert found is None  # Eliminación física (BaseRepository.delete)

    def test_list_all_telegram_users(self, repository, sample_telegram_user, inactive_telegram_user):
        """Test listar todos los usuarios (activos e inactivos)."""
        # Act
        users = repository.list_all()

        # Assert
        assert len(users) >= 2
        telegram_ids = [user.telegram_id for user in users]
        assert sample_telegram_user.telegram_id in telegram_ids
        assert inactive_telegram_user.telegram_id in telegram_ids


class TestTelegramUserRepositoryQueriesByTelegramId:
    """Tests para queries por telegram_id."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de TelegramUserRepository."""
        return TelegramUserRepository(db_session)

    def test_get_by_telegram_id_found(self, repository, sample_telegram_user):
        """Test búsqueda por telegram_id exitosa."""
        # Act
        found = repository.get_by_telegram_id(123456789)

        # Assert
        assert found is not None
        assert found.id == sample_telegram_user.id
        assert found.telegram_id == 123456789

    def test_get_by_telegram_id_not_found(self, repository):
        """Test búsqueda por telegram_id inexistente retorna None."""
        # Act
        found = repository.get_by_telegram_id(000000000)

        # Assert
        assert found is None

    def test_exists_by_telegram_id_true(self, repository, sample_telegram_user):
        """Test exists_by_telegram_id retorna True si existe."""
        # Act
        exists = repository.exists_by_telegram_id(123456789)

        # Assert
        assert exists is True

    def test_exists_by_telegram_id_false(self, repository):
        """Test exists_by_telegram_id retorna False si no existe."""
        # Act
        exists = repository.exists_by_telegram_id(000000000)

        # Assert
        assert exists is False


class TestTelegramUserRepositorySubscriptions:
    """Tests para gestión de suscripciones many-to-many."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de TelegramUserRepository."""
        return TelegramUserRepository(db_session)

    def test_subscribe_to_source(self, repository, sample_telegram_user, sample_source, db_session):
        """Test suscripción exitosa a una fuente."""
        # Act
        repository.subscribe_to_source(sample_telegram_user.id, sample_source.id)
        db_session.refresh(sample_telegram_user)

        # Assert
        assert len(sample_telegram_user.sources) == 1
        assert sample_source in sample_telegram_user.sources

    def test_subscribe_to_source_user_not_found(self, repository, sample_source):
        """Test suscripción con usuario inexistente lanza NotFoundError."""
        # Arrange
        fake_uuid = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.subscribe_to_source(fake_uuid, sample_source.id)

    def test_subscribe_to_source_source_not_found(self, repository, sample_telegram_user):
        """Test suscripción a fuente inexistente lanza NotFoundError."""
        # Arrange
        fake_uuid = uuid4()

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.subscribe_to_source(sample_telegram_user.id, fake_uuid)

    def test_subscribe_to_source_already_subscribed(self, repository, telegram_user_with_subscriptions, sample_source):
        """Test suscripción duplicada lanza AlreadyExistsError."""
        # Arrange - telegram_user_with_subscriptions ya está suscrito a sample_source

        # Act & Assert
        with pytest.raises(AlreadyExistsError):
            repository.subscribe_to_source(telegram_user_with_subscriptions.id, sample_source.id)

    def test_unsubscribe_from_source(self, repository, telegram_user_with_subscriptions, sample_source, db_session):
        """Test cancelación exitosa de suscripción."""
        # Arrange - Verificar que está suscrito inicialmente
        assert sample_source in telegram_user_with_subscriptions.sources

        # Act
        repository.unsubscribe_from_source(telegram_user_with_subscriptions.id, sample_source.id)
        db_session.refresh(telegram_user_with_subscriptions)

        # Assert
        assert len(telegram_user_with_subscriptions.sources) == 0
        assert sample_source not in telegram_user_with_subscriptions.sources

    def test_unsubscribe_from_source_not_subscribed(self, repository, sample_telegram_user, sample_source):
        """Test cancelar suscripción inexistente lanza NotFoundError."""
        # Arrange - sample_telegram_user NO está suscrito

        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.unsubscribe_from_source(sample_telegram_user.id, sample_source.id)

    def test_get_user_subscriptions(self, repository, telegram_user_with_subscriptions, sample_source):
        """Test obtener fuentes suscritas de un usuario."""
        # Act
        subscriptions = repository.get_user_subscriptions(telegram_user_with_subscriptions.id)

        # Assert
        assert len(subscriptions) == 1
        assert subscriptions[0].id == sample_source.id

    def test_get_user_subscriptions_empty(self, repository, sample_telegram_user):
        """Test obtener suscripciones de usuario sin suscripciones."""
        # Act
        subscriptions = repository.get_user_subscriptions(sample_telegram_user.id)

        # Assert
        assert len(subscriptions) == 0

    def test_get_source_subscribers(self, repository, sample_source, telegram_user_with_subscriptions, db_session):
        """Test obtener usuarios suscritos a una fuente."""
        # Act
        subscribers = repository.get_source_subscribers(sample_source.id)

        # Assert
        assert len(subscribers) >= 1
        subscriber_ids = [user.id for user in subscribers]
        assert telegram_user_with_subscriptions.id in subscriber_ids

    def test_get_source_subscribers_empty(self, repository, inactive_source):
        """Test obtener suscriptores de fuente sin suscriptores."""
        # Act
        subscribers = repository.get_source_subscribers(inactive_source.id)

        # Assert
        assert len(subscribers) == 0

    def test_get_users_subscribed_to_source_alias(self, repository, sample_source, telegram_user_with_subscriptions):
        """Test método alias get_users_subscribed_to_source funciona igual."""
        # Act
        subscribers = repository.get_users_subscribed_to_source(sample_source.id)

        # Assert
        assert len(subscribers) >= 1
        subscriber_ids = [user.id for user in subscribers]
        assert telegram_user_with_subscriptions.id in subscriber_ids

    def test_is_subscribed_true(self, repository, telegram_user_with_subscriptions, sample_source):
        """Test is_subscribed retorna True si está suscrito."""
        # Act
        result = repository.is_subscribed(telegram_user_with_subscriptions.id, sample_source.id)

        # Assert
        assert result is True

    def test_is_subscribed_false(self, repository, sample_telegram_user, sample_source):
        """Test is_subscribed retorna False si no está suscrito."""
        # Act
        result = repository.is_subscribed(sample_telegram_user.id, sample_source.id)

        # Assert
        assert result is False


class TestTelegramUserRepositoryConstraints:
    """Tests para constraints de unicidad."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de TelegramUserRepository."""
        return TelegramUserRepository(db_session)

    def test_unique_telegram_id_constraint(self, repository, sample_telegram_user, db_session):
        """Test que telegram_id debe ser único (IntegrityError en duplicado)."""
        # Arrange - Intentar crear usuario con telegram_id duplicado
        duplicate_user = TelegramUser(
            telegram_id=123456789,  # Ya existe
            username="different_user",
            first_name="Different"
        )

        # Act & Assert
        with pytest.raises(IntegrityError) as exc_info:
            repository.create(duplicate_user)

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


class TestTelegramUserRepositoryEdgeCases:
    """Tests para casos edge y escenarios especiales."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de TelegramUserRepository."""
        return TelegramUserRepository(db_session)

    def test_create_user_with_minimal_fields(self, repository, db_session):
        """Test creación con campos mínimos (solo telegram_id requerido)."""
        # Arrange
        user = TelegramUser(
            telegram_id=555666777,
            # username, first_name, last_name son opcionales
        )

        # Act
        created = repository.create(user)

        # Assert
        assert created.id is not None
        assert created.telegram_id == 555666777
        assert created.username is None
        assert created.first_name is None
        assert created.is_active is True  # Default
        assert created.bot_blocked is False  # Default
        assert created.language_code == "es"  # Default

    def test_bot_blocked_flag(self, repository, db_session):
        """Test gestión del flag bot_blocked."""
        # Arrange
        user = TelegramUser(
            telegram_id=444555666,
            username="blocked_user",
            bot_blocked=True,
            is_active=False
        )

        # Act
        created = repository.create(user)

        # Assert
        assert created.bot_blocked is True
        assert created.is_active is False

    def test_multiple_subscriptions(self, repository, sample_telegram_user, multiple_sources, db_session):
        """Test usuario con múltiples suscripciones."""
        # Arrange - Suscribir a 3 fuentes
        for source in multiple_sources[:3]:
            repository.subscribe_to_source(sample_telegram_user.id, source.id)

        # Act
        db_session.refresh(sample_telegram_user)
        subscriptions = repository.get_user_subscriptions(sample_telegram_user.id)

        # Assert
        assert len(subscriptions) == 3

    def test_language_code_variations(self, repository, db_session):
        """Test diferentes códigos de idioma."""
        # Arrange
        languages = ["es", "en", "pt", "fr", "de"]
        created_users = []

        # Act
        for i, lang in enumerate(languages):
            user = TelegramUser(
                telegram_id=100000000 + i,
                language_code=lang
            )
            created = repository.create(user)
            created_users.append(created)

        # Assert
        assert len(created_users) == 5
        for i, lang in enumerate(languages):
            assert created_users[i].language_code == lang

    def test_full_name_property(self, repository, db_session):
        """Test propiedad full_name del modelo."""
        # Arrange
        user = TelegramUser(
            telegram_id=777888999,
            first_name="John",
            last_name="Doe"
        )
        created = repository.create(user)

        # Act & Assert
        assert created.full_name == "John Doe"

    def test_display_name_property(self, repository, db_session):
        """Test propiedad display_name del modelo."""
        # Arrange - Usuario con username
        user1 = TelegramUser(
            telegram_id=111222333,
            username="john_doe",
            first_name="John"
        )
        created1 = repository.create(user1)

        # Arrange - Usuario sin username
        user2 = TelegramUser(
            telegram_id=444555666,
            first_name="Jane",
            last_name="Smith"
        )
        created2 = repository.create(user2)

        # Act & Assert
        assert created1.display_name == "@john_doe"
        assert created2.display_name == "Jane Smith"

    def test_subscription_count_property(self, repository, sample_telegram_user, multiple_sources, db_session):
        """Test propiedad subscription_count del modelo."""
        # Arrange - Sin suscripciones
        assert sample_telegram_user.subscription_count == 0

        # Act - Añadir 2 suscripciones
        repository.subscribe_to_source(sample_telegram_user.id, multiple_sources[0].id)
        repository.subscribe_to_source(sample_telegram_user.id, multiple_sources[1].id)
        db_session.refresh(sample_telegram_user)

        # Assert
        assert sample_telegram_user.subscription_count == 2

    def test_has_subscriptions_property(self, repository, sample_telegram_user, sample_source, db_session):
        """Test propiedad has_subscriptions del modelo."""
        # Arrange - Sin suscripciones
        assert sample_telegram_user.has_subscriptions is False

        # Act - Añadir suscripción
        repository.subscribe_to_source(sample_telegram_user.id, sample_source.id)
        db_session.refresh(sample_telegram_user)

        # Assert
        assert sample_telegram_user.has_subscriptions is True
