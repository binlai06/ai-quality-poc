"""Smoke checks: is the system up and serving its core data."""

import pytest

from framework.api.room_client import RoomClient
from framework.models.room import RoomList


@pytest.mark.api
@pytest.mark.smoke
def test_list_rooms_returns_200_and_at_least_one_room(room_client: RoomClient) -> None:
    response = room_client.list_rooms()

    assert response.status_code == 200
    room_list = RoomList.model_validate(response.json())
    assert len(room_list.rooms) >= 1
