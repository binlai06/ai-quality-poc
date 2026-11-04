"""Room service CRUD, called directly on its own port (local Docker only)."""

import pytest

from framework.api.room_client import RoomClient
from framework.cleanup import RoomCleanup
from framework.factories.room_factory import RoomFactory
from framework.models.room import Room, RoomList

pytestmark = [pytest.mark.api, pytest.mark.service]


@pytest.mark.smoke
def test_get_created_room_returns_same_room(
    service_room_client: RoomClient, created_room: Room
) -> None:
    response = service_room_client.get_room(created_room.roomid)

    assert response.status_code == 200
    assert Room.model_validate(response.json()) == created_room


@pytest.mark.regression
def test_create_room_returns_201_and_room(
    service_room_client: RoomClient, auth_token: str, room_cleanup: RoomCleanup
) -> None:
    payload = RoomFactory.build()

    response = service_room_client.create_room(payload.model_dump(), auth_token)
    room_cleanup.track(response)

    assert response.status_code == 201
    room = Room.model_validate(response.json())
    assert room.roomid > 0
    assert room.model_dump(exclude={"roomid"}) == payload.model_dump()


@pytest.mark.regression
def test_update_room_returns_202_and_updated_room(
    service_room_client: RoomClient, auth_token: str, created_room: Room
) -> None:
    new_fields = RoomFactory.build()

    response = service_room_client.update_room(
        created_room.roomid, new_fields.model_dump(), auth_token
    )

    assert response.status_code == 202
    room = Room.model_validate(response.json())
    assert room.roomid == created_room.roomid
    assert room.model_dump(exclude={"roomid"}) == new_fields.model_dump()


@pytest.mark.regression
def test_get_updated_room_returns_new_fields(
    service_room_client: RoomClient, auth_token: str, created_room: Room
) -> None:
    new_fields = RoomFactory.build()
    update = service_room_client.update_room(
        created_room.roomid, new_fields.model_dump(), auth_token
    )
    assert update.status_code == 202

    response = service_room_client.get_room(created_room.roomid)

    assert response.status_code == 200
    room = Room.model_validate(response.json())
    assert room.model_dump(exclude={"roomid"}) == new_fields.model_dump()


@pytest.mark.regression
def test_delete_room_returns_202(
    service_room_client: RoomClient, auth_token: str, created_room: Room
) -> None:
    response = service_room_client.delete_room(created_room.roomid, auth_token)

    assert response.status_code == 202


@pytest.mark.regression
def test_deleted_room_is_not_in_room_list(
    service_room_client: RoomClient, auth_token: str, created_room: Room
) -> None:
    deletion = service_room_client.delete_room(created_room.roomid, auth_token)
    assert deletion.status_code == 202

    response = service_room_client.list_rooms()

    assert response.status_code == 200
    room_ids = {room.roomid for room in RoomList.model_validate(response.json()).rooms}
    assert created_room.roomid not in room_ids
