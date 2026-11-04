"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest

from framework.api.auth_client import AuthClient
from framework.api.room_client import RoomClient


@pytest.fixture(scope="session")
def auth_client() -> Iterator[AuthClient]:
    """One AuthClient per test session, closed at the end."""
    with AuthClient() as client:
        yield client


@pytest.fixture(scope="session")
def room_client() -> Iterator[RoomClient]:
    """One RoomClient per test session, closed at the end."""
    with RoomClient() as client:
        yield client
