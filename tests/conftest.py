"""Shared pytest fixtures."""

from collections.abc import Iterator

import pytest

from framework import config
from framework.api.auth_client import AuthClient
from framework.api.room_client import RoomClient
from framework.cleanup import RoomCleanup
from framework.factories.room_factory import RoomFactory
from framework.models.auth import LoginResponse
from framework.models.room import Room


@pytest.fixture(scope="session")
def auth_client() -> Iterator[AuthClient]:
    """One AuthClient per test session, closed at the end."""
    with AuthClient() as client:
        yield client


@pytest.fixture(scope="session")
def auth_token(auth_client: AuthClient) -> str:
    """Admin token, logged in once per session (once per worker under xdist)."""
    settings = config.settings
    response = auth_client.login(settings.admin_username, settings.admin_password)
    assert response.status_code == 200, f"admin login failed: {response.status_code}"
    return LoginResponse.model_validate(response.json()).token


@pytest.fixture(scope="session")
def proxy_room_client() -> Iterator[RoomClient]:
    """Room endpoints through the UI proxy."""
    with RoomClient.via_proxy() as client:
        yield client


@pytest.fixture(scope="session")
def service_room_client() -> Iterator[RoomClient]:
    """Room service called directly."""
    with RoomClient.direct() as client:
        yield client


@pytest.fixture
def room_cleanup(
    service_room_client: RoomClient, auth_token: str
) -> Iterator[RoomCleanup]:
    """Deletes every room a test registers with `track()`, after the test."""
    cleanup = RoomCleanup(service_room_client, auth_token)
    yield cleanup
    cleanup.delete_all()


@pytest.fixture
def created_room(
    service_room_client: RoomClient, auth_token: str, room_cleanup: RoomCleanup
) -> Room:
    """A fresh room, created through the room service and deleted after the test."""
    response = service_room_client.create_room(
        RoomFactory.build().model_dump(), auth_token
    )
    room_cleanup.track(response)
    assert response.status_code == 201, f"room setup failed: {response.status_code}"
    return Room.model_validate(response.json())
