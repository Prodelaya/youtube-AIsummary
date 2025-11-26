"""
Tests unitarios para UserRepository.

Cubre:
- CRUD básico de usuarios
- Búsquedas por username y email
- Soft delete (is_active=False)
- Validación de constraints únicos
- Gestión de usuarios activos

Requiere PostgreSQL en Docker: docker-compose up -d postgres
"""

import pytest
from sqlalchemy.exc import IntegrityError

from src.models.user import User
from src.repositories.user_repository import UserRepository
from src.repositories.exceptions import NotFoundError


class TestUserRepositoryCRUD:
    """Tests para operaciones CRUD básicas de UserRepository."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de UserRepository."""
        return UserRepository(db_session)

    def test_create_user(self, repository, db_session):
        """Test creación exitosa de usuario."""
        # Arrange
        user = User(
            username="johndoe",
            email="john@example.com",
            hashed_password="$2b$12$hashed_password_here",
            role="user",
        )

        # Act
        created = repository.create(user)

        # Assert
        assert created.id is not None
        assert created.username == "johndoe"
        assert created.email == "john@example.com"
        assert created.role == "user"
        assert created.is_active is True  # Default
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_get_by_id_found(self, repository, sample_user):
        """Test búsqueda de usuario por ID exitosa."""
        # Act
        found = repository.get_by_id(sample_user.id)

        # Assert
        assert found.id == sample_user.id
        assert found.username == sample_user.username
        assert found.email == sample_user.email

    def test_get_by_id_not_found(self, repository):
        """Test búsqueda de usuario inexistente lanza NotFoundError."""
        # Act & Assert
        with pytest.raises(NotFoundError) as exc_info:
            repository.get_by_id(99999)

        assert "User" in str(exc_info.value)
        assert "99999" in str(exc_info.value)

    def test_update_user(self, repository, sample_user, db_session):
        """Test actualización exitosa de usuario."""
        # Arrange
        sample_user.email = "newemail@example.com"
        sample_user.role = "admin"

        # Act
        updated = repository.update(sample_user)

        # Assert
        assert updated.id == sample_user.id
        assert updated.email == "newemail@example.com"
        assert updated.role == "admin"
        assert updated.updated_at > updated.created_at  # Timestamp actualizado

    def test_delete_user_soft_delete(self, repository, sample_user, db_session):
        """Test eliminación lógica de usuario (soft delete)."""
        # Arrange
        user_id = sample_user.id

        # Act
        repository.delete(user_id)

        # Assert
        user = db_session.get(User, user_id)
        assert user is not None  # No se elimina físicamente
        assert user.is_active is False  # Soft delete

    def test_delete_user_not_found(self, repository):
        """Test eliminar usuario inexistente lanza NotFoundError."""
        # Act & Assert
        with pytest.raises(NotFoundError):
            repository.delete(99999)


class TestUserRepositoryQueries:
    """Tests para queries especializadas de UserRepository."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de UserRepository."""
        return UserRepository(db_session)

    def test_get_by_username_found(self, repository, sample_user):
        """Test búsqueda por username exitosa."""
        # Act
        found = repository.get_by_username("admin")

        # Assert
        assert found is not None
        assert found.id == sample_user.id
        assert found.username == "admin"

    def test_get_by_username_not_found(self, repository):
        """Test búsqueda por username inexistente retorna None."""
        # Act
        found = repository.get_by_username("nonexistent")

        # Assert
        assert found is None

    def test_get_by_email_found(self, repository, sample_user):
        """Test búsqueda por email exitosa."""
        # Act
        found = repository.get_by_email("admin@test.com")

        # Assert
        assert found is not None
        assert found.id == sample_user.id
        assert found.email == "admin@test.com"

    def test_get_by_email_not_found(self, repository):
        """Test búsqueda por email inexistente retorna None."""
        # Act
        found = repository.get_by_email("nonexistent@example.com")

        # Assert
        assert found is None

    def test_get_all_active(self, repository, sample_user, regular_user, db_session):
        """Test obtener solo usuarios activos."""
        # Arrange - Desactivar un usuario
        regular_user.is_active = False
        db_session.commit()

        # Act
        active_users = repository.get_all_active()

        # Assert
        assert len(active_users) == 1  # Solo sample_user está activo
        assert active_users[0].id == sample_user.id
        assert active_users[0].is_active is True

    def test_get_all_active_empty(self, repository, sample_user, db_session):
        """Test get_all_active cuando no hay usuarios activos."""
        # Arrange - Desactivar todos
        sample_user.is_active = False
        db_session.commit()

        # Act
        active_users = repository.get_all_active()

        # Assert
        assert len(active_users) == 0


class TestUserRepositoryConstraints:
    """Tests para constraints de unicidad en UserRepository."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de UserRepository."""
        return UserRepository(db_session)

    def test_unique_username_constraint(self, repository, sample_user, db_session):
        """Test que username debe ser único (IntegrityError en duplicado)."""
        # Arrange - Intentar crear usuario con username duplicado
        duplicate_user = User(
            username="admin",  # Username ya existe
            email="different@example.com",
            hashed_password="$2b$12$hash",
            role="user",
        )

        # Act & Assert
        with pytest.raises(IntegrityError) as exc_info:
            repository.create(duplicate_user)

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()

    def test_unique_email_constraint(self, repository, sample_user, db_session):
        """Test que email debe ser único (IntegrityError en duplicado)."""
        # Arrange - Intentar crear usuario con email duplicado
        duplicate_user = User(
            username="different_user",
            email="admin@test.com",  # Email ya existe
            hashed_password="$2b$12$hash",
            role="user",
        )

        # Act & Assert
        with pytest.raises(IntegrityError) as exc_info:
            repository.create(duplicate_user)

        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower()


class TestUserRepositoryEdgeCases:
    """Tests para casos edge de UserRepository."""

    @pytest.fixture
    def repository(self, db_session):
        """Fixture que proporciona instancia de UserRepository."""
        return UserRepository(db_session)

    def test_create_user_with_minimal_fields(self, repository, db_session):
        """Test creación con campos mínimos requeridos."""
        # Arrange
        user = User(
            username="minimal",
            email="minimal@example.com",
            hashed_password="$2b$12$hash",
            role="user",  # Role tiene default pero lo especificamos
        )

        # Act
        created = repository.create(user)

        # Assert
        assert created.id is not None
        assert created.is_active is True  # Default value
        assert created.role == "user"

    def test_create_user_with_all_roles(self, repository, db_session):
        """Test creación de usuarios con diferentes roles."""
        # Arrange
        roles = ["admin", "user", "bot"]
        created_users = []

        # Act
        for role in roles:
            user = User(
                username=f"user_{role}",
                email=f"{role}@example.com",
                hashed_password="$2b$12$hash",
                role=role,
            )
            created = repository.create(user)
            created_users.append(created)

        # Assert
        assert len(created_users) == 3
        for i, role in enumerate(roles):
            assert created_users[i].role == role

    def test_password_is_stored_hashed(self, repository, db_session):
        """Test que las contraseñas se almacenan hasheadas."""
        # Arrange
        hashed_password = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5NU8KQDpTMWBq"
        user = User(
            username="secure_user",
            email="secure@example.com",
            hashed_password=hashed_password,
            role="user",
        )

        # Act
        created = repository.create(user)

        # Assert
        assert created.hashed_password == hashed_password
        assert created.hashed_password.startswith("$2b$")  # bcrypt hash format
        assert len(created.hashed_password) == 60  # bcrypt hash length

    def test_get_all_active_with_mixed_states(self, repository, db_session):
        """Test get_all_active con mix de usuarios activos/inactivos."""
        # Arrange - Crear 3 activos y 2 inactivos
        for i in range(5):
            user = User(
                username=f"user{i}",
                email=f"user{i}@example.com",
                hashed_password="$2b$12$hash",
                role="user",
                is_active=(i < 3),  # Primeros 3 activos, últimos 2 inactivos
            )
            db_session.add(user)
        db_session.commit()

        # Act
        active_users = repository.get_all_active()

        # Assert
        assert len(active_users) == 3
        for user in active_users:
            assert user.is_active is True
