"""
Excepciones personalizadas para la capa de repositories.

Estas excepciones permiten un manejo de errores más específico
y facilitan la traducción a códigos HTTP en la capa de API.
"""

from typing import Any
from uuid import UUID


class RepositoryError(Exception):
    """
    Excepción base para errores de la capa de repositorio.

    Todas las excepciones custom de repositories heredan de esta.
    Útil para capturar cualquier error de repositorio con un solo except.
    """

    pass


class NotFoundError(RepositoryError):
    """
    Se lanza cuando no se encuentra un recurso por su ID.

    Uso típico:
        source = repo.get_by_id(source_id)
        if not source:
            raise NotFoundError("Source", source_id)
    """

    def __init__(self, resource_type: str, resource_id: UUID | str | int):
        self.resource_type = resource_type
        self.resource_id = resource_id
        super().__init__(f"{resource_type} con id '{resource_id}' no encontrado")


class AlreadyExistsError(RepositoryError):
    """
    Se lanza cuando se intenta crear un recurso que ya existe.

    Típicamente por violación de constraint UNIQUE (ej: URL duplicada).

    Uso típico:
        if repo.exists_by_url(url):
            raise AlreadyExistsError("Source", "url", url)
    """

    def __init__(self, resource_type: str, field_name: str, field_value: Any):
        self.resource_type = resource_type
        self.field_name = field_name
        self.field_value = field_value
        super().__init__(f"{resource_type} con {field_name}='{field_value}' ya existe")
