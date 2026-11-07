"""Respuestas de error documentadas en OpenAPI."""

from pydantic import BaseModel


class ErrorRespuesta(BaseModel):
    detail: str


_DESCRIPCIONES = {
    400: "Solicitud inválida.",
    401: "No autenticado: falta el token, es inválido o expiró.",
    402: "Puntos insuficientes.",
    403: "Sin permiso: rol no autorizado, cuenta de otro cliente, menor de edad o cliente autoexcluido.",
    404: "Recurso no encontrado.",
    409: "Conflicto con el estado actual del recurso.",
    422: "Datos de entrada inválidos.",
    423: "Cuenta bloqueada temporalmente por intentos fallidos.",
}


def errores(*codigos: int) -> dict:
    """Construye el parámetro `responses` de una ruta para los códigos indicados."""
    return {
        codigo: {"model": ErrorRespuesta, "description": _DESCRIPCIONES[codigo]}
        for codigo in codigos
        if codigo != 422  # FastAPI ya documenta 422 con HTTPValidationError
    }
