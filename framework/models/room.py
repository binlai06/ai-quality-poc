"""Pydantic models for the room service and its UI proxy."""

from pydantic import BaseModel


class RoomPayload(BaseModel):
    """Room fields a client sends on create and update."""

    roomName: str
    type: str
    accessible: bool
    image: str
    description: str
    features: list[str]
    roomPrice: int


class Room(RoomPayload):
    """A room as returned by the room service, including its id."""

    roomid: int


class RoomList(BaseModel):
    """Response body of the room list endpoint."""

    rooms: list[Room]


class ServiceError(BaseModel):
    """Validation error body returned by the room service itself."""

    errorCode: int
    error: str
    errorMessage: str
    fieldErrors: list[str]


class ProxyErrors(BaseModel):
    """Error body returned by the UI proxy for room calls."""

    errors: list[str]
