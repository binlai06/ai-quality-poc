"""Test settings, read from environment variables with defaults for the local Docker setup."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by every API client and test."""

    base_url: str
    timeout: float


def load_settings() -> Settings:
    """Build settings from the environment.

    RBP_BASE_URL: root URL of the RBP UI, which proxies every service under /api.
    RBP_TIMEOUT: request timeout in seconds.
    """
    return Settings(
        base_url=os.getenv("RBP_BASE_URL", "http://localhost").rstrip("/"),
        timeout=float(os.getenv("RBP_TIMEOUT", "10")),
    )


settings = load_settings()
