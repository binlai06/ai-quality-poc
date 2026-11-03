"""Pydantic models for the room service responses."""

from pydantic import BaseModel


class Room(BaseModel):
    """A single room as returned by the room service."""

    roomid: int
    roomName: str
    type: str
    accessible: bool
    image: str
    description: str
    features: list[str]
    roomPrice: int


class RoomList(BaseModel):
    """Response body of GET /api/room."""

    rooms: list[Room]
