"""Test settings, read from environment variables with defaults for the local Docker setup."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings shared by every API client and test."""

    base_url: str
    room_url: str
    timeout: float
    admin_username: str
    admin_password: str


def load_settings() -> Settings:
    """Build settings from the environment.

    RBP_BASE_URL: root URL of the RBP UI, which proxies every service under /api.
    RBP_ROOM_URL: room service called directly (not exposed on the backup environment).
    RBP_TIMEOUT: request timeout in seconds.
    RBP_ADMIN_USERNAME / RBP_ADMIN_PASSWORD: admin login. Defaults are RBP's public demo values.
    """
    return Settings(
        base_url=os.getenv("RBP_BASE_URL", "http://localhost").rstrip("/"),
        room_url=os.getenv("RBP_ROOM_URL", "http://localhost:3001").rstrip("/"),
        timeout=float(os.getenv("RBP_TIMEOUT", "10")),
        admin_username=os.getenv("RBP_ADMIN_USERNAME", "admin"),
        admin_password=os.getenv("RBP_ADMIN_PASSWORD", "password"),
    )


settings = load_settings()
