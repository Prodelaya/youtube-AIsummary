"""
Repository para operaciones CRUD de usuarios.

Gestiona el acceso a datos de la tabla users, incluyendo
búsquedas por username, email y operaciones de autenticación.
"""


from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.user import User
from src.repositories.exceptions import NotFoundError


class UserRepository:
    """
    Repository para gestión de usuarios (autenticación y autorización).

    Proporciona métodos optimizados para operaciones comunes:
    - Creación de usuarios
    - Búsqueda por username/email (para login)
    - Actualización de credenciales
    - Soft delete (is_active=False)

    Attributes:
        session: Sesión activa de SQLAlchemy.
    """

    def __init__(self, session: Session):
        """
        Inicializa el repository con una sesión de base de datos.

        Args:
            session: Sesión activa de SQLAlchemy.
        """
        self.session = session

    def create(self, user: User) -> User:
        """
        Crea un nuevo usuario en la base de datos.

        Args:
            user: Instancia de User con datos a insertar.

        Returns:
            User: Usuario creado con ID asignado.

        Notes:
            - El password debe estar hasheado ANTES de llamar a este método.
            - Los timestamps se asignan automáticamente.
        """
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user

    def get_by_id(self, user_id: int) -> User:
        """
        Busca un usuario por ID.

        Args:
            user_id: ID del usuario.

        Returns:
            User: Usuario encontrado.

        Raises:
            NotFoundError: Si no existe usuario con ese ID.
        """
        user = self.session.get(User, user_id)
        if not user:
            raise NotFoundError(resource_type="User", resource_id=user_id)
        return user

    def get_by_username(self, username: str) -> User | None:
        """
        Busca un usuario por nombre de usuario.

        Args:
            username: Nombre de usuario (único).

        Returns:
            User | None: Usuario encontrado o None si no existe.

        Notes:
            - Usa índice único en username para búsqueda rápida.
            - Devuelve None si no existe (no lanza excepción).
        """
        stmt = select(User).where(User.username == username)
        return self.session.scalars(stmt).first()

    def get_by_email(self, email: str) -> User | None:
        """
        Busca un usuario por email.

        Args:
            email: Email del usuario (único).

        Returns:
            User | None: Usuario encontrado o None si no existe.

        Notes:
            - Usa índice único en email para búsqueda rápida.
            - Devuelve None si no existe (no lanza excepción).
        """
        stmt = select(User).where(User.email == email)
        return self.session.scalars(stmt).first()

    def update(self, user: User) -> User:
        """
        Actualiza un usuario existente.

        Args:
            user: Instancia de User con cambios a persistir.

        Returns:
            User: Usuario actualizado.

        Notes:
            - updated_at se actualiza automáticamente.
        """
        self.session.commit()
        self.session.refresh(user)
        return user

    def delete(self, user_id: int) -> None:
        """
        Elimina lógicamente un usuario (soft delete).

        Args:
            user_id: ID del usuario a eliminar.

        Raises:
            NotFoundError: Si no existe usuario con ese ID.

        Notes:
            - No elimina físicamente el registro (is_active=False).
            - Para eliminar físicamente: session.delete(user).
        """
        user = self.get_by_id(user_id)
        user.is_active = False
        self.session.commit()

    def get_all_active(self) -> list[User]:
        """
        Obtiene todos los usuarios activos.

        Returns:
            list[User]: Lista de usuarios activos (is_active=True).

        Notes:
            - Útil para listados administrativos.
        """
        stmt = select(User).where(User.is_active == True)  # noqa: E712
        return list(self.session.scalars(stmt).all())
