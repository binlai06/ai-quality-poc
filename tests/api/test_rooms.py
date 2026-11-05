"""Room service CRUD, called directly on its own port (local Docker only)."""

import threading
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pytest
import requests
from faker import Faker

from framework.api.room_client import RoomClient
from framework.cleanup import RoomCleanup
from framework.factories.room_factory import MAX_PRICE, MIN_PRICE, RoomFactory
from framework.models.room import Room, RoomList, ServiceError

# Issue D: concurrent creates can return another client's room. Every test that creates
# rooms must stay in this file, which `--dist loadfile` (pytest.ini) runs on one worker.
pytestmark = [pytest.mark.api, pytest.mark.service]

fake = Faker()

MISSING = object()
"""Marks a field to leave out of the payload entirely."""

NAME_REQUIRED = "Room name must be set"
TYPE_REQUIRED = "Type must be set"
TYPE_INVALID = (
    "Type can only contain the room options Single, Double, Twin, Family or Suite"
)
PRICE_TOO_LOW = f"must be greater than or equal to {MIN_PRICE}"
PRICE_TOO_HIGH = f"must be less than or equal to {MAX_PRICE}"


def payload_with(**changes: Any) -> dict[str, Any]:
    """A valid factory payload with some fields replaced, or removed when set to MISSING."""
    payload = RoomFactory.build().model_dump()
    for field, value in changes.items():
        if value is MISSING:
            payload.pop(field)
        else:
            payload[field] = value
    return payload


@pytest.fixture
def unknown_room_id(service_room_client: RoomClient) -> int:
    """An id far above every existing room, so it cannot exist now or soon."""
    response = service_room_client.list_rooms()
    if response.status_code != 200:
        pytest.fail(f"listing rooms failed: {response.status_code}")
    room_ids = [room.roomid for room in RoomList.model_validate(response.json()).rooms]
    return max(room_ids, default=0) + 1_000_000


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
@pytest.mark.parametrize(
    "price",
    [
        pytest.param(MIN_PRICE, id="price-min"),
        pytest.param(MAX_PRICE, id="price-max"),
    ],
)
def test_create_room_with_boundary_price_returns_201(
    service_room_client: RoomClient,
    auth_token: str,
    room_cleanup: RoomCleanup,
    price: int,
) -> None:
    payload = RoomFactory.build(roomPrice=price)

    response = service_room_client.create_room(payload.model_dump(), auth_token)
    room_cleanup.track(response)

    assert response.status_code == 201
    room = Room.model_validate(response.json())
    assert room.roomPrice == price


@pytest.mark.regression
def test_update_room_returns_202_and_updated_room(
    service_room_client: RoomClient,
    auth_token: str,
    created_room: Room,
    room_cleanup: RoomCleanup,
) -> None:
    new_fields = RoomFactory.build()

    response = service_room_client.update_room(
        created_room.roomid, new_fields.model_dump(), auth_token
    )
    room_cleanup.track(response)

    assert response.status_code == 202
    room = Room.model_validate(response.json())
    assert room.roomid == created_room.roomid
    assert room.model_dump(exclude={"roomid"}) == new_fields.model_dump()


@pytest.mark.regression
def test_get_updated_room_returns_new_fields(
    service_room_client: RoomClient,
    auth_token: str,
    created_room: Room,
    room_cleanup: RoomCleanup,
) -> None:
    new_fields = RoomFactory.build()
    update = service_room_client.update_room(
        created_room.roomid, new_fields.model_dump(), auth_token
    )
    room_cleanup.track(update)
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


INVALID_CREATE_PAYLOADS = [
    pytest.param({"roomName": MISSING}, NAME_REQUIRED, id="missing-name"),
    pytest.param({"roomName": ""}, NAME_REQUIRED, id="empty-name"),
    pytest.param({"type": MISSING}, TYPE_REQUIRED, id="missing-type"),
    pytest.param({"type": "Penthouse"}, TYPE_INVALID, id="invalid-type"),
    pytest.param({"roomPrice": -5}, PRICE_TOO_LOW, id="negative-price"),
    pytest.param({"roomPrice": MIN_PRICE - 1}, PRICE_TOO_LOW, id="price-below-min"),
    pytest.param({"roomPrice": MAX_PRICE + 1}, PRICE_TOO_HIGH, id="price-above-max"),
    pytest.param({"roomPrice": MISSING}, PRICE_TOO_LOW, id="missing-price"),
]


@pytest.mark.regression
@pytest.mark.parametrize(("changes", "expected_error"), INVALID_CREATE_PAYLOADS)
def test_create_room_with_invalid_payload_returns_400(
    service_room_client: RoomClient,
    auth_token: str,
    room_cleanup: RoomCleanup,
    changes: dict[str, Any],
    expected_error: str,
) -> None:
    payload = payload_with(**changes)

    response = service_room_client.create_room(payload, auth_token)
    room_cleanup.track(response)

    assert response.status_code == 400
    error = ServiceError.model_validate(response.json())
    assert expected_error in error.fieldErrors


@pytest.mark.regression
@pytest.mark.parametrize(
    ("changes", "expected_error"),
    [
        pytest.param({"roomName": ""}, NAME_REQUIRED, id="empty-name"),
        pytest.param({"type": "Penthouse"}, TYPE_INVALID, id="invalid-type"),
        pytest.param({"roomPrice": -5}, PRICE_TOO_LOW, id="negative-price"),
    ],
)
def test_update_room_with_invalid_payload_returns_400(
    service_room_client: RoomClient,
    auth_token: str,
    created_room: Room,
    changes: dict[str, Any],
    expected_error: str,
) -> None:
    payload = payload_with(**changes)

    response = service_room_client.update_room(created_room.roomid, payload, auth_token)

    assert response.status_code == 400
    error = ServiceError.model_validate(response.json())
    assert expected_error in error.fieldErrors


WriteCall = Callable[[RoomClient, int, str | None], requests.Response]

WRITE_OPERATIONS: dict[str, WriteCall] = {
    "create": lambda client, _room_id, token: client.create_room(
        RoomFactory.build().model_dump(), token
    ),
    "update": lambda client, room_id, token: client.update_room(
        room_id, RoomFactory.build().model_dump(), token
    ),
    "delete": lambda client, room_id, token: client.delete_room(room_id, token),
}


@pytest.mark.regression
@pytest.mark.parametrize("operation", list(WRITE_OPERATIONS))
@pytest.mark.parametrize(
    "token",
    [
        pytest.param(None, id="missing-token"),
        pytest.param(fake.pystr(min_chars=16, max_chars=16), id="invalid-token"),
    ],
)
def test_room_write_without_valid_token_returns_403(
    service_room_client: RoomClient,
    created_room: Room,
    room_cleanup: RoomCleanup,
    operation: str,
    token: str | None,
) -> None:
    write = WRITE_OPERATIONS[operation]

    response = write(service_room_client, created_room.roomid, token)
    room_cleanup.track(response)

    assert response.status_code == 403


@pytest.mark.regression
def test_update_unknown_room_returns_404(
    service_room_client: RoomClient, auth_token: str, unknown_room_id: int
) -> None:
    payload = RoomFactory.build().model_dump()

    response = service_room_client.update_room(unknown_room_id, payload, auth_token)

    assert response.status_code == 404


@pytest.mark.regression
def test_delete_unknown_room_returns_404(
    service_room_client: RoomClient, auth_token: str, unknown_room_id: int
) -> None:
    response = service_room_client.delete_room(unknown_room_id, auth_token)

    assert response.status_code == 404


# Known bug #4: the room service answers 500 instead of 404 when the room does not exist.


@pytest.mark.regression
@pytest.mark.issue("4")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #4: GET of an unknown room returns 500 instead of 404",
)
def test_get_unknown_room_returns_404(
    service_room_client: RoomClient, unknown_room_id: int
) -> None:
    response = service_room_client.get_room(unknown_room_id)

    assert response.status_code == 404


@pytest.mark.regression
@pytest.mark.issue("4")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #4: GET of a deleted room returns 500 instead of 404",
)
def test_get_deleted_room_returns_404(
    service_room_client: RoomClient, auth_token: str, created_room: Room
) -> None:
    deletion = service_room_client.delete_room(created_room.roomid, auth_token)
    if deletion.status_code != 202:
        pytest.fail(f"room setup failed, delete returned {deletion.status_code}")

    response = service_room_client.get_room(created_room.roomid)

    assert response.status_code == 404


# Known bug #2: through the UI proxy every /api/room/{id} request returns 500. These tests
# need a room to change, so they create it through the room service and live in this file.
# Tests that only read through the proxy are in test_rooms_proxy.py.


@pytest.mark.regression
@pytest.mark.issue("2")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #2: proxy PUT /api/room/{id} returns 500",
)
def test_proxy_update_room_returns_200(
    proxy_room_client: RoomClient,
    auth_token: str,
    created_room: Room,
    room_cleanup: RoomCleanup,
) -> None:
    new_fields = RoomFactory.build()

    response = proxy_room_client.update_room(
        created_room.roomid, new_fields.model_dump(), auth_token
    )
    room_cleanup.track(response)

    assert response.status_code == 200
    assert response.json() == {"success": True}


@pytest.mark.regression
@pytest.mark.issue("2")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #2: proxy DELETE /api/room/{id} returns 500",
)
def test_proxy_delete_room_returns_200(
    proxy_room_client: RoomClient, auth_token: str, created_room: Room
) -> None:
    response = proxy_room_client.delete_room(created_room.roomid, auth_token)

    assert response.status_code == 200
    assert response.json() == {"success": True}


CONCURRENT_CREATES = 20
CONCURRENT_ROUNDS = 5


@pytest.mark.regression
@pytest.mark.race
@pytest.mark.issue("D")
@pytest.mark.xfail(
    raises=AssertionError,
    strict=False,
    reason="RBP bug D: concurrent creates can return another client's room. "
    "Measured on 2026-11-04: 54 of 60 solo runs (90%) hit the bug with 5 rounds of "
    "20 creates, so strict=True would fail about 1 run in 10.",
)
def test_concurrent_creates_return_the_room_that_was_sent(
    auth_token: str, room_cleanup: RoomCleanup
) -> None:
    rounds = [
        [RoomFactory.build().model_dump() for _ in range(CONCURRENT_CREATES)]
        for _ in range(CONCURRENT_ROUNDS)
    ]

    def create_round(payloads: list[dict[str, Any]]) -> list[requests.Response]:
        barrier = threading.Barrier(CONCURRENT_CREATES, timeout=10)

        def create(payload: dict[str, Any]) -> requests.Response:
            with RoomClient.direct() as client:
                barrier.wait()
                return client.create_room(payload, auth_token)

        with ThreadPoolExecutor(max_workers=CONCURRENT_CREATES) as pool:
            return list(pool.map(create, payloads))

    responses_per_round = [create_round(payloads) for payloads in rounds]
    for responses in responses_per_round:
        for response in responses:
            room_cleanup.track(response)

    statuses = {r.status_code for responses in responses_per_round for r in responses}
    assert statuses == {201}
    mismatches = [
        (round_number, sent["roomName"], response.json()["roomName"])
        for round_number, (payloads, responses) in enumerate(
            zip(rounds, responses_per_round, strict=True), start=1
        )
        for sent, response in zip(payloads, responses, strict=True)
        if response.json()["roomName"] != sent["roomName"]
    ]
    assert not mismatches, (
        f"{len(mismatches)} responses returned a different room: {mismatches}"
    )
