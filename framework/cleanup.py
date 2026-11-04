"""Helpers that delete test data after a test."""

import json

import requests

from framework.api.room_client import RoomClient
from framework.models.room import RoomList


class RoomCleanup:
    """Deletes rooms a test created, found by the unique name the test sent.

    The name comes from the request, not the response: under concurrent creates the
    room in a response can belong to another client (RBP bug D), so its id is not
    trustworthy. Cleanup lists the rooms and deletes the ones whose name matches.
    """

    def __init__(self, client: RoomClient, token: str) -> None:
        self._client = client
        self._token = token
        self._names: set[str] = set()

    def track(self, response: requests.Response) -> None:
        """Remember the room name sent in the request behind this response."""
        body = response.request.body
        if not body:
            return
        name = json.loads(body).get("roomName")
        if name:
            self._names.add(name)

    def delete_all(self) -> None:
        """Delete every tracked room still present. A room a test deleted itself is skipped."""
        if not self._names:
            return
        listing = self._client.list_rooms()
        assert listing.status_code == 200, f"cleanup list failed: {listing.status_code}"
        for room in RoomList.model_validate(listing.json()).rooms:
            if room.roomName in self._names:
                response = self._client.delete_room(room.roomid, self._token)
                assert response.status_code in (202, 404), (
                    f"cleanup of room {room.roomid} failed: {response.status_code}"
                )
