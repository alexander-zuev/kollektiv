from enum import Enum

from src.models.base_models import Environment


class AllowedOrigins(str, Enum):
    """Allowed origins for CORS."""

    LOCAL = "*"  # Allow all origins for local development
    STAGING = [
        "https://staging.thekollektiv.ai",
        "https://*.railway.app",
        "https://*.up.railway.app",
        "https://*.railway.internal",
    ]
    PRODUCTION = [
        "https://thekollektiv.ai",
        "https://*.railway.app",
        "https://*.up.railway.app",
        "https://*.railway.internal",
    ]


def get_cors_config(environment: Environment) -> dict:
    """Get the CORS configuration based on the environment."""
    return {
        "allow_origins": AllowedOrigins[environment.value.upper()].value,
        "allow_credentials": True,
        "allow_methods": ["GET", "POST", "OPTIONS", "DELETE", "PATCH", "PUT"],
        "allow_headers": [
            "Authorization",
            "Content-Type",
            "X-Request-ID",
            "baggage",
            "sentry-trace",
        ],
    }
