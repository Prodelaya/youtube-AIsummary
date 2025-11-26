"""
Fixtures compartidas para tests del bot de Telegram.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session, sessionmaker
from telegram import Chat, Message, Update, User

from src.models.base import Base


@pytest.fixture
def mock_telegram_user():
    """
    Fixture que crea un usuario de Telegram mock.

    Returns:
        Usuario mock con datos de prueba
    """
    user = MagicMock(spec=User)
    user.id = 123456789
    user.username = "test_user"
    user.first_name = "Test"
    user.last_name = "User"
    user.is_bot = False
    return user


@pytest.fixture
def mock_chat():
    """
    Fixture que crea un chat de Telegram mock.

    Returns:
        Chat mock (tipo privado)
    """
    chat = MagicMock(spec=Chat)
    chat.id = 123456789
    chat.type = "private"
    return chat


@pytest.fixture
def mock_message(mock_telegram_user, mock_chat):
    """
    Fixture que crea un mensaje de Telegram mock.

    Args:
        mock_telegram_user: Usuario mock
        mock_chat: Chat mock

    Returns:
        Mensaje mock con reply_text async
    """
    message = MagicMock(spec=Message)
    message.from_user = mock_telegram_user
    message.chat = mock_chat
    message.text = "/start"
    message.reply_text = AsyncMock()
    return message


@pytest.fixture
def mock_update(mock_message, mock_telegram_user):
    """
    Fixture que crea un Update de Telegram mock.

    Args:
        mock_message: Mensaje mock
        mock_telegram_user: Usuario mock

    Returns:
        Update mock completo
    """
    update = MagicMock(spec=Update)
    update.message = mock_message
    update.effective_message = mock_message
    update.effective_user = mock_telegram_user
    update.effective_chat = mock_message.chat
    return update


@pytest.fixture
def mock_context():
    """
    Fixture que crea un contexto de Telegram mock.

    Returns:
        Context mock básico
    """
    context = MagicMock()
    context.bot = MagicMock()
    context.user_data = {}
    context.chat_data = {}
    return context


@pytest.fixture
def db_session() -> Session:
    """
    Crea una sesión de BD para tests (reutiliza fixture de API).

    Usa la BD real de desarrollo (requiere PostgreSQL corriendo).

    Yields:
        Sesión de SQLAlchemy con BD temporal
    """
    from src.core.database import engine

    # Crear todas las tablas
    Base.metadata.create_all(engine)

    # Crear sesión
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        # Rollback para deshacer cambios del test
        session.rollback()
        session.close()
        # Limpiar todas las tablas
        Base.metadata.drop_all(engine)
