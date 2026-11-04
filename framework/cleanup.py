"""Helpers that delete test data after a test."""

import requests

from framework.api.room_client import RoomClient


class RoomCleanup:
    """Remembers rooms a test created and deletes them through the room service."""

    def __init__(self, client: RoomClient, token: str) -> None:
        self._client = client
        self._token = token
        self._room_ids: list[int] = []

    def track(self, response: requests.Response) -> None:
        """Register the room from a create response, if one was created."""
        if response.status_code == 201:
            self._room_ids.append(response.json()["roomid"])

    def delete_all(self) -> None:
        """Delete every tracked room. 404 is fine: the test may have deleted it itself."""
        for room_id in self._room_ids:
            response = self._client.delete_room(room_id, self._token)
            assert response.status_code in (202, 404), (
                f"cleanup of room {room_id} failed: {response.status_code}"
            )
