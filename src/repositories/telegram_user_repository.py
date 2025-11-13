"""
Repository para el modelo TelegramUser (usuarios del bot).

Extiende BaseRepository con métodos específicos para gestionar
usuarios de Telegram y sus suscripciones a fuentes (relación M:N).
"""

from uuid import UUID

from sqlalchemy.orm import Session

from src.models import Source, TelegramUser
from src.repositories.base_repository import BaseRepository
from src.repositories.exceptions import AlreadyExistsError, NotFoundError


class TelegramUserRepository(BaseRepository[TelegramUser]):
    """
    Repository específico para el modelo TelegramUser.

    Hereda operaciones CRUD de BaseRepository y añade:
    - Búsqueda por telegram_id (ID único de Telegram)
    - Gestión de suscripciones M:N con Source
    - Queries para obtener usuarios suscritos a un canal
    - Queries para obtener canales de un usuario
    """

    def __init__(self, session: Session):
        """
        Inicializa el repository con una sesión de SQLAlchemy.

        Args:
            session: Sesión activa de SQLAlchemy
        """
        super().__init__(session, TelegramUser)

    def get_by_telegram_id(self, telegram_id: int) -> TelegramUser | None:
        """
        Busca un usuario por su ID de Telegram.

        Args:
            telegram_id: ID único de Telegram (bigint)

        Returns:
            TelegramUser si existe, None si no existe

        Example:
            user = repo.get_by_telegram_id(123456789)
            if not user:
                user = TelegramUser(telegram_id=123456789, ...)
                repo.create(user)
        """
        return (
            self.session.query(TelegramUser).filter(TelegramUser.telegram_id == telegram_id).first()
        )

    def exists_by_telegram_id(self, telegram_id: int) -> bool:
        """
        Verifica si existe un usuario con ese ID de Telegram.

        Args:
            telegram_id: ID de Telegram a verificar

        Returns:
            True si existe, False si no

        Example:
            if not repo.exists_by_telegram_id(telegram_id):
                # Usuario nuevo, registrar
                pass
        """
        return (
            self.session.query(TelegramUser.id)
            .filter(TelegramUser.telegram_id == telegram_id)
            .first()
            is not None
        )

    def subscribe_to_source(self, user_id: UUID, source_id: UUID) -> None:
        """
        Suscribe un usuario a una fuente.

        Crea entrada en tabla intermedia user_source_subscriptions.

        Args:
            user_id: UUID del usuario
            source_id: UUID de la fuente

        Raises:
            NotFoundError: Si usuario o fuente no existe
            AlreadyExistsError: Si ya está suscrito

        Example:
            repo.subscribe_to_source(user_id, source_id)
        """
        user = self.get_by_id(user_id)
        source = self.session.get(Source, source_id)

        if source is None:
            raise NotFoundError("Source", source_id)

        if source in user.sources:
            raise AlreadyExistsError(
                "Subscription", "user_id + source_id", f"{user_id} → {source_id}"
            )

        user.sources.append(source)
        self.session.commit()

    def unsubscribe_from_source(self, user_id: UUID, source_id: UUID) -> None:
        """
        Cancela suscripción de un usuario a una fuente.

        Elimina entrada en tabla intermedia user_source_subscriptions.

        Args:
            user_id: UUID del usuario
            source_id: UUID de la fuente

        Raises:
            NotFoundError: Si usuario, fuente o suscripción no existe

        Example:
            repo.unsubscribe_from_source(user_id, source_id)
        """
        user = self.get_by_id(user_id)
        source = self.session.get(Source, source_id)

        if source is None:
            raise NotFoundError("Source", source_id)

        if source not in user.sources:
            raise NotFoundError("Subscription", f"{user_id} → {source_id}")

        user.sources.remove(source)
        self.session.commit()

    def get_user_subscriptions(self, user_id: UUID) -> list[Source]:
        """
        Obtiene todas las fuentes a las que está suscrito un usuario.

        Args:
            user_id: UUID del usuario

        Returns:
            Lista de fuentes (sources) a las que está suscrito

        Example:
            sources = repo.get_user_subscriptions(user_id)
            for source in sources:
                print(f"Suscrito a: {source.name}")
        """
        user = self.get_by_id(user_id)
        return user.sources

    def get_source_subscribers(self, source_id: UUID) -> list[TelegramUser]:
        """
        Obtiene todos los usuarios suscritos a una fuente.

        Usado por worker de distribución para saber a quién enviar resúmenes.

        Args:
            source_id: UUID de la fuente

        Returns:
            Lista de usuarios suscritos a esa fuente

        Example:
            subscribers = repo.get_source_subscribers(source_id)
            for user in subscribers:
                send_to_telegram(user.telegram_id, summary)
        """
        source = self.session.get(Source, source_id)

        if source is None:
            raise NotFoundError("Source", source_id)

        return source.users

    def get_users_subscribed_to_source(self, source_id: UUID) -> list[TelegramUser]:
        """
        Obtiene todos los usuarios suscritos a una fuente (alias para get_source_subscribers).

        Este método es un alias conveniente para distribución de resúmenes.

        Args:
            source_id: UUID de la fuente

        Returns:
            Lista de usuarios suscritos a esa fuente

        Example:
            subscribers = repo.get_users_subscribed_to_source(source_id)
            for user in subscribers:
                distribute_summary_to_user(user, summary)
        """
        return self.get_source_subscribers(source_id)

    def is_subscribed(self, user_id: UUID, source_id: UUID) -> bool:
        """
        Verifica si un usuario está suscrito a una fuente.

        Args:
            user_id: UUID del usuario
            source_id: UUID de la fuente

        Returns:
            True si está suscrito, False si no

        Example:
            if repo.is_subscribed(user_id, source_id):
                # Mostrar botón con ✅
            else:
                # Mostrar botón con ❌
        """
        user = self.get_by_id(user_id)
        source = self.session.get(Source, source_id)

        if source is None:
            return False

        return source in user.sources
