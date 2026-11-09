"""Helpers that delete test data after a test."""

import json

import requests

from framework.api.booking_client import BookingClient
from framework.api.message_client import MessageClient
from framework.api.room_client import RoomClient
from framework.models.message import MessageList
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
        if listing.status_code != 200:
            raise RuntimeError(f"cleanup list failed: {listing.status_code}")
        for room in RoomList.model_validate(listing.json()).rooms:
            if room.roomName in self._names:
                response = self._client.delete_room(room.roomid, self._token)
                if response.status_code not in (202, 404):
                    raise RuntimeError(
                        f"cleanup of room {room.roomid} failed: {response.status_code}"
                    )


class MessageCleanup:
    """Deletes contact messages a UI test created, found by their unique subject.

    The UI never shows the message id, so the test registers the subject it typed.
    Teardown lists the messages, deletes those with a tracked subject and treats 404
    (already gone) as fine. Any other failure raises RuntimeError("message cleanup ..."),
    which no xfail(raises=AssertionError) can absorb, so it is never mistaken for a known bug.
    """

    def __init__(self, client: MessageClient, token: str) -> None:
        self._client = client
        self._token = token
        self._subjects: set[str] = set()

    def track(self, subject: str) -> None:
        """Remember a subject to delete in teardown. Call right after submitting."""
        self._subjects.add(subject)

    def delete_all(self) -> None:
        if not self._subjects:
            return
        listing = self._client.list_messages()
        if listing.status_code != 200:
            raise RuntimeError(
                f"message cleanup: list failed with {listing.status_code}"
            )
        for message in MessageList.model_validate(listing.json()).messages:
            if message.subject in self._subjects:
                response = self._client.delete_message(message.id, self._token)
                if response.status_code not in (202, 404):
                    raise RuntimeError(
                        f"message cleanup: delete of message {message.id} "
                        f"failed with {response.status_code}"
                    )


class BookingCleanup:
    """Deletes bookings a test created, then the "new booking" message each one triggered.

    Rooms are not handled here: deleting a room does not delete its bookings, so the
    test must use this cleanup together with the room fixture, which runs after it.
    The booking id comes from a 201 response. The message is found by the guest name
    sent in the request (the service stores it as "<firstname> <lastname>").
    """

    MESSAGE_SUBJECT = "You have a new booking!"

    def __init__(
        self, booking_client: BookingClient, message_client: MessageClient, token: str
    ) -> None:
        self._bookings = booking_client
        self._messages = message_client
        self._token = token
        self._booking_ids: set[int] = set()
        self._guest_names: set[str] = set()

    def track(self, response: requests.Response) -> None:
        """Remember the booking and guest behind this create response. Call it before asserting."""
        body = response.request.body
        if body:
            guest = json.loads(body)
            self._guest_names.add(f"{guest.get('firstname')} {guest.get('lastname')}")
        if response.status_code == 201:
            self._booking_ids.add(response.json()["bookingid"])

    def delete_all(self) -> None:
        """Delete tracked bookings, then their messages. A 404 means already gone."""
        for booking_id in self._booking_ids:
            response = self._bookings.delete_booking(booking_id, self._token)
            if response.status_code not in (202, 404):
                raise RuntimeError(
                    f"booking cleanup: delete of booking {booking_id} "
                    f"failed with {response.status_code}"
                )
        if not self._guest_names:
            return
        listing = self._messages.list_messages()
        if listing.status_code != 200:
            raise RuntimeError(
                f"booking cleanup: message list failed with {listing.status_code}"
            )
        for message in MessageList.model_validate(listing.json()).messages:
            if (
                message.subject == self.MESSAGE_SUBJECT
                and message.name in self._guest_names
            ):
                response = self._messages.delete_message(message.id, self._token)
                if response.status_code not in (202, 404):
                    raise RuntimeError(
                        f"booking cleanup: delete of message {message.id} "
                        f"failed with {response.status_code}"
                    )
