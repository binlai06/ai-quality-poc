"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest

from framework.api.room_client import RoomClient


@pytest.fixture(scope="session")
def room_client() -> Iterator[RoomClient]:
    """One RoomClient per test session, closed at the end."""
    with RoomClient() as client:
        yield client
