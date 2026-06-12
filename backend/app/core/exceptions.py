import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("AgentForge.Exceptions")

class BaseAppException(Exception):
    """Base exception for AgentForge application errors."""
    def __init__(self, detail: str, status_code: int = 400, error_type: str = "ApplicationError"):
        self.detail = detail
        self.status_code = status_code
        self.error_type = error_type
        super().__init__(detail)

class DatabaseIntegrityError(BaseAppException):
    def __init__(self, detail: str):
        super().__init__(detail, status_code=status.HTTP_409_CONFLICT, error_type="DatabaseConflict")

class ConfigurationError(BaseAppException):
    def __init__(self, detail: str):
        super().__init__(detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, error_type="ConfigurationError")

def register_exception_handlers(app: FastAPI):
    """Register central handlers on the FastAPI application."""
    
    @app.exception_handler(BaseAppException)
    async def app_exception_handler(request: Request, exc: BaseAppException):
        logger.error(f"Application error: {exc.detail}", extra={"error_type": exc.error_type})
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "type": exc.error_type,
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.warning(f"HTTP exception: {exc.detail} (Status: {exc.status_code})")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "detail": exc.detail,
                "type": "HTTPError",
                "status_code": exc.status_code
            }
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Request validation validation failure: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": exc.errors(),
                "type": "RequestValidationError",
                "status_code": 422
            }
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled server exception encountered.")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected internal server error occurred.",
                "type": "InternalServerError",
                "status_code": 500
            }
        )
