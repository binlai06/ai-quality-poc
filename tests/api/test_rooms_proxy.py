"""Room endpoints through the UI proxy, for tests that create and change nothing.

These run on every environment, including the backup site. Tests that need a room to
change create it through the room service, so they live in test_rooms.py.
"""

import pytest
from faker import Faker

from framework.api.room_client import RoomClient
from framework.factories.room_factory import RoomFactory
from framework.models.room import ProxyErrors, Room, RoomList

pytestmark = [pytest.mark.api, pytest.mark.regression]

fake = Faker()


@pytest.fixture
def existing_room_id(proxy_room_client: RoomClient) -> int:
    """Id of a room that was not created by a test, taken from the proxy list."""
    response = proxy_room_client.list_rooms()
    if response.status_code != 200:
        pytest.fail(f"listing rooms failed: {response.status_code}")
    rooms = RoomList.model_validate(response.json()).rooms
    permanent = [room for room in rooms if not room.roomName.startswith("qa-")]
    if not permanent:
        pytest.fail("no permanent room to read")
    return permanent[0].roomid


def test_proxy_create_room_without_token_returns_401(
    proxy_room_client: RoomClient,
) -> None:
    payload = RoomFactory.build().model_dump()

    response = proxy_room_client.create_room(payload, token=None)

    assert response.status_code == 401
    ProxyErrors.model_validate(response.json())


@pytest.mark.issue("2")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #2: proxy GET /api/room/{id} returns 500",
)
def test_proxy_get_room_returns_200_and_room(
    proxy_room_client: RoomClient, existing_room_id: int
) -> None:
    response = proxy_room_client.get_room(existing_room_id)

    assert response.status_code == 200
    assert Room.model_validate(response.json()).roomid == existing_room_id


@pytest.mark.issue("3")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #3: proxy POST /api/room with an invalid token returns 500",
)
def test_proxy_create_room_with_invalid_token_returns_401_or_403(
    proxy_room_client: RoomClient,
) -> None:
    payload = RoomFactory.build().model_dump()
    invalid_token = fake.pystr(min_chars=16, max_chars=16)

    response = proxy_room_client.create_room(payload, invalid_token)

    assert response.status_code in (401, 403)
