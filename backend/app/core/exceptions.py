"""
Standardized Exception Handling

Provides consistent error responses across the API with structured format:
{
    "detail": "Human-readable message",  // Backward compat
    "error": {
        "code": "ERROR_CODE",
        "message": "Human-readable message",
        "details": {...}
    }
}
"""

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Any, Dict, Optional
from app.core.logging_config import get_logger

logger = get_logger()


class APIException(HTTPException):
    """
    Base exception for API errors with structured response
    
    Usage:
        raise APIException(400, "INSUFFICIENT_FUNDS", "Not enough balance",
                          {"available": 100, "requested": 150})
    """
    
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.code = code
        self.message = message
        self.details = details or {}
        
        # Create structured error response with backward compatibility
        error_detail = {
            "detail": message,  # Backward compat for tests
            "error": {
                "code": code,
                "message": message,
            }
        }
        
        if details:
            error_detail["error"]["details"] = details
        
        super().__init__(status_code=status_code, detail=error_detail)


# Common exceptions with predefined codes

class MarketNotFoundException(APIException):
    """Market not found"""
    def __init__(self, market_id: int):
        super().__init__(
            404,
            "MARKET_NOT_FOUND",
            f"Market with ID {market_id} does not exist",
            {"market_id": market_id}
        )


class InsufficientFundsException(APIException):
    """Not enough balance"""
    def __init__(self, available: float, requested: float):
        super().__init__(
            400,
            "INSUFFICIENT_FUNDS",
            f"Insufficient balance. Available: {available}₽, Requested: {requested}₽",
            {"available_rubles": available, "requested_rubles": requested}
        )


class OrderNotFoundException(APIException):
    """Order not found"""
    def __init__(self, order_id: int):
        super().__init__(
            404,
            "ORDER_NOT_FOUND",
            f"Order with ID {order_id} does not exist",
            {"order_id": order_id}
        )


class UnauthorizedOrderAccessException(APIException):
    """Attempting to access another user's order"""
    def __init__(self, order_id: int):
        super().__init__(
            403,
            "UNAUTHORIZED_ORDER_ACCESS",
            "You do not have permission to access this order",
            {"order_id": order_id}
        )


class InvalidOrderSizeException(APIException):
    """Order size out of bounds"""
    def __init__(self, amount: float, min_amount: float, max_amount: float):
        super().__init__(
            400,
            "INVALID_ORDER_SIZE",
            f"Order size must be between {min_amount}₽ and {max_amount}₽",
            {
                "amount": amount,
                "min_amount": min_amount,
                "max_amount": max_amount
            }
        )


class MarketResolvedException(APIException):
    """Market already resolved"""
    def __init__(self, market_id: int):
        super().__init__(
            400,
            "MARKET_RESOLVED",
            "Cannot place orders on resolved market",
            {"market_id": market_id}
        )


class InvalidPriceException(APIException):
    """Invalid price value"""
    def __init__(self, price: float, message: str = "Price must be between 0.01 and 0.99"):
        super().__init__(
            400,
            "INVALID_PRICE",
            message,
            {"price": price}
        )


# Exception handler for logging

async def api_exception_handler(request: Request, exc: APIException):
    """
    Global exception handler for APIException
    
    Logs the error and returns structured JSON response
    """
    logger.warning(
        f"API Exception: {exc.code}",
        extra={
            "code": exc.code,
            "error_message": exc.message,
            "details": exc.details,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail
    )


# Generic HTTP exception handler for consistency

async def http_exception_handler(request: Request, exc: HTTPException):
    """
    Handler for standard HTTPException to ensure consistent format
    """
    # If detail is already structured (dict), use as-is
    if isinstance(exc.detail, dict):
        content = exc.detail
    else:
        # Convert to structured format with backward compat
        content = {
            "detail": str(exc.detail),
            "error": {
                "code": "HTTP_ERROR",
                "message": str(exc.detail)
            }
        }
    
    logger.warning(
        f"HTTP Exception: {exc.status_code}",
        extra={
            "status_code": exc.status_code,
            "detail": exc.detail,
            "path": request.url.path,
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=content
    )
