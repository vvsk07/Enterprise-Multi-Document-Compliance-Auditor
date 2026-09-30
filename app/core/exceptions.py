"""
Centralized Application Exception Classes and FastAPI Exception Handlers.
Returns clean, structured error responses without leaking internal stack traces.
"""

from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.core.logging import logger

class BaseAuditorException(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)

class DocumentNotFoundException(BaseAuditorException):
    def __init__(self, document_id: str):
        super().__init__(
            code="DOCUMENT_NOT_FOUND",
            message=f"Document '{document_id}' was not found.",
            status_code=404
        )

class RuleNotFoundException(BaseAuditorException):
    def __init__(self, rule_id: str):
        super().__init__(
            code="RULE_NOT_FOUND",
            message=f"Compliance rule '{rule_id}' was not found.",
            status_code=404
        )

class UnauthorizedException(BaseAuditorException):
    def __init__(self, message: str = "Invalid or missing API key."):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401
        )

class RateLimitExceededException(BaseAuditorException):
    def __init__(self, message: str = "Rate limit exceeded. Please try again later."):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429
        )

class ValidationException(BaseAuditorException):
    def __init__(self, message: str):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400
        )

async def auditor_exception_handler(request: Request, exc: BaseAuditorException):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.warning(f"[{request_id}] Handled Exception {exc.code}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "request_id": request_id
            }
        }
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    request_id = getattr(request.state, "request_id", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "request_id": request_id
            }
        }
    )

async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = getattr(request.state, "request_id", "unknown")
    logger.error(f"[{request_id}] Unhandled Exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An internal server error occurred.",
                "request_id": request_id
            }
        }
    )
