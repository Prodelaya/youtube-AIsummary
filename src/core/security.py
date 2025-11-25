"""
Módulo de seguridad: Password hashing y verificación.

Utiliza bcrypt para hashear y verificar contraseñas de forma segura.
Bcrypt es el estándar recomendado por OWASP para almacenar passwords.

Referencias:
    - https://owasp.org/www-project-cheat-sheets/cheatsheets/Password_Storage_Cheat_Sheet
    - https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
"""

import bcrypt


def hash_password(password: str) -> str:
    """
    Hashea una contraseña en texto plano usando bcrypt.

    Args:
        password: Contraseña en texto plano.

    Returns:
        str: Hash bcrypt de la contraseña (60 caracteres).

    Notes:
        - Cada llamada genera un hash diferente (salt aleatorio).
        - Es seguro hashear la misma password varias veces.
        - El hash incluye el salt, no es necesario almacenarlo separadamente.
        - Usa 12 rondas por defecto (balance seguridad/performance).

    Examples:
        >>> hash_password("changeme123")
        '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIBx0fqvXe'

        >>> # Cada llamada genera un hash diferente
        >>> hash_password("changeme123")
        '$2b$12$anotherHashWithDifferentSalt...'
    """
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verifica si una contraseña en texto plano coincide con su hash.

    Args:
        plain_password: Contraseña en texto plano (del usuario).
        hashed_password: Hash bcrypt almacenado en BD.

    Returns:
        bool: True si la password es correcta, False en caso contrario.

    Notes:
        - Resistente a timing attacks (tiempo constante).
        - Maneja automáticamente diferentes versiones de bcrypt.

    Examples:
        >>> hashed = hash_password("changeme123")
        >>> verify_password("changeme123", hashed)
        True

        >>> verify_password("wrongpassword", hashed)
        False
    """
    password_bytes = plain_password.encode("utf-8")
    hashed_bytes = hashed_password.encode("utf-8")
    return bcrypt.checkpw(password_bytes, hashed_bytes)
