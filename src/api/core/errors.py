"""
RFC 7807 Problem Details error handling for API endpoints.

Provides consistent error responses across all API endpoints following
the Problem Details for HTTP APIs specification (RFC 7807).

Error response format:
{
    "type": "https://api.shopify-supplier.com/errors/{error_type}",
    "title": "{Human-readable title}",
    "status": {HTTP status code},
    "detail": "{Specific error message}",
    "fields": {...}  # Extension for validation errors only
}

Usage:
    from src.api.core.errors import ProblemDetails, register_error_handlers

    # In route handler
    return ProblemDetails.not_found("Product", sku)

    # In app factory
    register_error_handlers(app)
"""
from typing import Any
from flask import jsonify, Flask, request
from pydantic import ValidationError
from werkzeug.exceptions import HTTPException


class ProblemDetails:
    """
    RFC 7807 Problem Details response builder.

    Provides static methods for common error types that return
    Flask-compatible (response, status_code) tuples.
    """

    BASE_URI = "https://api.shopify-supplier.com/errors"

    @staticmethod
    def validation_error(error: ValidationError, status: int = 400):
        """
        Convert Pydantic ValidationError to Problem Details with field-level errors.

        Args:
            error: Pydantic ValidationError instance
            status: HTTP status code (default: 400)

        Returns:
            Tuple of (JSON response, status code)
        """
        # Extract field-level errors from Pydantic
        fields = {}
        for err in error.errors():
            field_path = " -> ".join(str(loc) for loc in err["loc"])
            fields[field_path] = err["msg"]

        response = {
            "type": f"{ProblemDetails.BASE_URI}/validation-error",
            "title": "Validation Failed",
            "status": status,
            "detail": "Request validation failed on one or more fields",
            "fields": fields
        }
        return jsonify(response), status

    @staticmethod
    def business_error(
        error_type: str,
        title: str,
        detail: str,
        status: int = 400,
        **extensions
    ):
        """
        Generic business logic error with optional extensions.

        Args:
            error_type: Error type identifier (e.g., "insufficient-credits")
            title: Human-readable error title
            detail: Specific error message
            status: HTTP status code (default: 400)
            **extensions: Additional fields to include in response

        Returns:
            Tuple of (JSON response, status code)
        """
        response = {
            "type": f"{ProblemDetails.BASE_URI}/{error_type}",
            "title": title,
            "status": status,
            "detail": detail,
            **extensions
        }
        return jsonify(response), status

    @staticmethod
    def not_found(resource: str, identifier: Any):
        """
        404 Not Found error for missing resources.

        Args:
            resource: Resource type (e.g., "Product", "Job", "Vendor")
            identifier: Resource identifier (SKU, ID, etc.)

        Returns:
            Tuple of (JSON response, 404)
        """
        response = {
            "type": f"{ProblemDetails.BASE_URI}/not-found",
            "title": "Resource Not Found",
            "status": 404,
            "detail": f"{resource} with identifier '{identifier}' not found",
            "resource": resource,
            "identifier": str(identifier)
        }
        return jsonify(response), 404

    @staticmethod
    def rate_limit_exceeded(retry_after: str):
        """
        429 Too Many Requests error with retry information.

        Args:
            retry_after: Time when client can retry (e.g., "60 seconds")

        Returns:
            Tuple of (JSON response, 429)
        """
        safe_retry_after = str(retry_after).strip() if retry_after is not None else ""
        if not safe_retry_after or safe_retry_after.lower() == "none":
            safe_retry_after = "a short while"

        response = {
            "type": f"{ProblemDetails.BASE_URI}/rate-limit-exceeded",
            "title": "Rate Limit Exceeded",
            "status": 429,
            "detail": f"Rate limit exceeded. Please retry after {safe_retry_after}",
            "retry_after": safe_retry_after
        }
        return jsonify(response), 429

    @staticmethod
    def unauthorized(detail: str = "Authentication required"):
        """
        401 Unauthorized error for missing/invalid authentication.

        Args:
            detail: Specific error message (default: "Authentication required")

        Returns:
            Tuple of (JSON response, 401)
        """
        response = {
            "type": f"{ProblemDetails.BASE_URI}/unauthorized",
            "title": "Unauthorized",
            "status": 401,
            "detail": detail
        }
        return jsonify(response), 401

    @staticmethod
    def forbidden(detail: str = "Insufficient permissions"):
        """
        403 Forbidden error for insufficient permissions.

        Args:
            detail: Specific error message (default: "Insufficient permissions")

        Returns:
            Tuple of (JSON response, 403)
        """
        response = {
            "type": f"{ProblemDetails.BASE_URI}/forbidden",
            "title": "Forbidden",
            "status": 403,
            "detail": detail
        }
        return jsonify(response), 403


def register_error_handlers(app: Flask):
    """
    Register RFC 7807 error handlers for the Flask app.

    Handles:
    - Pydantic ValidationError
    - Werkzeug HTTPException
    - Flask-Limiter RateLimitExceeded
    - Common HTTP errors (404, 401, 403, 429, 500)
    - Generic Exception catch-all

    Security:
    - Production mode: Generic error messages, no stack traces
    - Development mode: Detailed errors for debugging

    Args:
        app: Flask application instance
    """

    @app.errorhandler(ValidationError)
    def handle_validation_error(e: ValidationError):
        """Handle Pydantic validation errors."""
        return ProblemDetails.validation_error(e)

    @app.errorhandler(HTTPException)
    def handle_http_exception(e: HTTPException):
        """Handle Werkzeug HTTP exceptions."""
        response = {
            "type": f"{ProblemDetails.BASE_URI}/http-error",
            "title": e.name,
            "status": e.code,
            "detail": e.description
        }
        return jsonify(response), e.code

    # Import here to avoid circular dependency if limiter not initialized yet
    try:
        from flask_limiter.errors import RateLimitExceeded

        @app.errorhandler(RateLimitExceeded)
        def handle_rate_limit_exceeded(e: RateLimitExceeded):
            """Handle Flask-Limiter rate limit errors."""
            # Extract retry_after from exception if available
            retry_after = getattr(e, 'retry_after', None)
            if retry_after is None:
                headers = e.get_headers() if hasattr(e, "get_headers") else None
                if isinstance(headers, dict):
                    retry_after = headers.get("Retry-After")
                elif isinstance(headers, list):
                    retry_after = dict(headers).get("Retry-After")
            return ProblemDetails.rate_limit_exceeded(retry_after)
    except ImportError:
        # Flask-Limiter not installed yet, skip registration
        pass

    @app.errorhandler(404)
    def handle_404(e):
        """Handle 404 Not Found errors."""
        response = {
            "type": f"{ProblemDetails.BASE_URI}/not-found",
            "title": "Not Found",
            "status": 404,
            "detail": f"The requested URL was not found: {request.path}"
        }
        return jsonify(response), 404

    @app.errorhandler(401)
    def handle_401(e):
        """Handle 401 Unauthorized errors."""
        return ProblemDetails.unauthorized()

    @app.errorhandler(403)
    def handle_403(e):
        """Handle 403 Forbidden errors."""
        return ProblemDetails.forbidden()

    @app.errorhandler(429)
    def handle_429(e):
        """Handle 429 Too Many Requests errors."""
        return ProblemDetails.rate_limit_exceeded("60 seconds")

    @app.errorhandler(500)
    def handle_500(e):
        """Handle 500 Internal Server Error."""
        # Check if running in production mode
        is_production = not app.debug and app.config.get("ENV") == "production"

        if is_production:
            # Sanitize error in production - no stack traces
            response = {
                "type": f"{ProblemDetails.BASE_URI}/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred. Please try again later."
            }
        else:
            # Development mode - provide detailed error
            response = {
                "type": f"{ProblemDetails.BASE_URI}/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": str(e),
                "debug": {
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
            }
        return jsonify(response), 500

    @app.errorhandler(Exception)
    def handle_generic_exception(e: Exception):
        """
        Catch-all handler for unhandled exceptions.

        Logs the error and returns sanitized response in production.
        """
        # Log the error for debugging
        app.logger.error(f"Unhandled exception: {type(e).__name__}: {str(e)}", exc_info=True)

        # Check if running in production mode
        is_production = not app.debug and app.config.get("ENV") == "production"

        if is_production:
            # Sanitize error in production
            response = {
                "type": f"{ProblemDetails.BASE_URI}/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": "An unexpected error occurred. Please try again later."
            }
        else:
            # Development mode - provide detailed error
            response = {
                "type": f"{ProblemDetails.BASE_URI}/internal-error",
                "title": "Internal Server Error",
                "status": 500,
                "detail": str(e),
                "debug": {
                    "exception_type": type(e).__name__,
                    "message": str(e)
                }
            }
        return jsonify(response), 500
