"""Client for the RBP room service."""

import requests

from framework.api.base_client import BaseClient


class RoomClient(BaseClient):
    """Calls the room service through the UI proxy at /api/room."""

    ROOM_PATH = "/api/room"

    def list_rooms(self) -> requests.Response:
        """GET all rooms. Returns the raw response so tests can assert on status and body."""
        return self.get(self.ROOM_PATH)
