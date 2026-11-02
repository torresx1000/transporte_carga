"""Consistent API error responses."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Any = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


def _error(code: str, message: str, details: Any, status_code: int) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "details": details},
    )


async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
    return _error(exc.code, exc.message, exc.details, exc.status_code)


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail
    message = detail if isinstance(detail, str) else "La solicitud no pudo completarse"
    details = None if isinstance(detail, str) else detail
    return _error(f"HTTP_{exc.status_code}", message, details, exc.status_code)


async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    return _error(
        "VALIDATION_ERROR",
        "Los datos enviados no son válidos",
        jsonable_encoder(exc.errors()),
        422,
    )


async def unexpected_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return _error(
        "INTERNAL_SERVER_ERROR",
        "Ocurrió un error interno",
        None,
        500,
    )


def register_error_handlers(app: FastAPI) -> None:
    """Register the shared error envelope for HTTP, validation and server errors."""
    app.add_exception_handler(ApiError, api_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)
