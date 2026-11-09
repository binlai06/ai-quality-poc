---
name: test-writing-conventions
description: "Test-writing conventions for the AI Quality POC: pytest API tests and Playwright UI tests. Use when writing, changing or reviewing tests, factories, cleanup classes or page objects."
---

# Test-writing conventions

Examples are real code. Copy the pattern, not the values. CLAUDE.md and `.claude/agents/` win on any conflict.

## 1. Test structure (Arrange-Act-Assert)
Arrange in fixtures or factories, one Act, then assert in this order: status code, schema (pydantic), business rules.
From `tests/api/test_booking_service.py`:
```python
@pytest.mark.regression
def test_create_booking_for_existing_room_returns_201_and_appears_in_room_summary(
    booking_client: BookingClient, booking_cleanup: BookingCleanup, created_room: Room,
) -> None:
    payload = BookingFactory.build(created_room.roomid)

    response = booking_client.create_booking(payload.model_dump(mode="json"))
    booking_cleanup.track(response)

    assert response.status_code == 201
    created = CreatedBooking.model_validate(response.json())
    assert created.booking.roomid == created_room.roomid
```
Tests never call `requests`; they use the clients in `framework/api/`. URLs come from `framework/config.py`.

## 2. Naming
- Tests: `test_<behaviour>_<expected_result>`, e.g. `test_create_room_with_boundary_price_returns_201`.
- There is no `__init__.py` in `tests/`, so every test file name must be unique across ALL of `tests/`.
  `tests/api/test_booking_service.py` and `tests/ui/test_booking.py` coexist only because the names differ.

## 3. Markers
- Layer: `api` or `ui`. Suite: `smoke` or `regression`. Both on every test.
- `service` when the test calls a service port directly (local Docker only).
- `story("BOOK-1")` for user stories. `issue("<number>")` ONLY for GitHub issues, never for a story.
- Module-wide markers go in `pytestmark = [pytest.mark.api, pytest.mark.service, pytest.mark.story("BOOK-1")]`.
- Markers are strict (`--strict-markers`): register new ones in `pytest.ini`, which needs user approval.

## 4. Data and cleanup
- Data comes from factories (`RoomFactory`, `GuestFactory`, `BookingFactory`) with a unique tag:
  `f"qa-room-{uuid.uuid4().hex[:8]}"`, guest `f"qa{tag}"`. Override single fields: `RoomFactory.build(roomPrice=price)`.
- Register cleanup RIGHT AFTER the creating action and BEFORE any assertion:
  `response = ...create_booking(...)` then `booking_cleanup.track(response)` then `assert ...`.
  Do it even on a negative test: the create may succeed by mistake.
- Fixture order decides teardown order. `booking_cleanup` depends on `created_room`, so teardown runs
  booking, then message, then room (deleting a room does not delete its bookings).
- Cleanup treats 404 as "already gone"; any other failure raises `RuntimeError`, never `AssertionError`.
- Never assert on totals or list lengths of shared data: parallel tests add and remove rows.
  Assert on your own tagged item instead.

## 5. Negative and boundary cases
- Use `pytest.param(..., id="...")` with a readable explicit id. Required when values are random (xdist needs the same ids on every worker):
```python
pytest.param({"firstname": fake.lexify("?" * 2)}, ["size must be between 3 and 18"], id="firstname-too-short"),
```
- Test values just outside each limit (`MIN_PRICE - 1`, `MAX_PRICE + 1`) AND the valid edges (`MIN_PRICE`, `MAX_PRICE`, ids `price-min`, `price-max`).
- A name must match what it asserts. `..._and_creates_nothing` must assert that nothing exists
  (the booking test reads the room summary and expects `bookings == []`).
- Verify real behaviour with curl before asserting it; do not assert from reading the source.

## 6. Known bugs
- API pattern (`tests/api/test_rooms.py`):
```python
@pytest.mark.regression
@pytest.mark.issue("4")
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="RBP bug #4: GET of an unknown room returns 500 instead of 404",
)
```
- The reason always starts with `RBP bug #<n>:`. `strict=True` makes a fixed bug fail loudly. `raises=AssertionError` stops setup errors hiding as a known bug.
- UI xfails (`tests/ui/test_booking.py`): the first line after Arrange is `expect(<page-ready element>).to_be_visible()`,
  so only the real failure after it is absorbed, not a page that never loaded.
- Never change a test silently to make it pass. Changing assertions or xfail markers needs user approval; report the bug with curl evidence instead.

## 7. Before you report
Run all of these and quote the REAL output (never claim a pass without running it):
```bash
ruff check . && ruff format --check .
.venv/bin/python -m pytest -n auto -m "not race"
curl -s http://localhost:3001/room/ | grep -o '"roomName":"qa-room-[a-z0-9]*"'
curl -s http://localhost:3006/message/ | grep -o "qa-subject-[a-z0-9]*"
curl -s http://localhost:3006/message/ | grep -o 'qa[0-9a-f]\{8\} Guest[0-9a-f]\{8\}'
```
The three curl commands must print nothing (leak check). Known bugs show as `xfailed`, never `failed` or `error`.
Run new tests alone first, then again with `-n auto`, then the whole suite.

## 8. Playwright (`framework/pages/`)
- Locator order: role or label first (`get_by_role("button", name="Submit")`, `get_by_label("Name", exact=True)`),
  then test id (`get_by_test_id("ContactDescription")`), then CSS only inside the page object, with a comment saying why:
  `# CSS only: the error box is a <div class="alert alert-danger"> without role=alert.`
- Tests never use raw selectors. Page objects extend `BasePage` or are components (`ContactForm`).
- Page objects expose actions and return `Locator`s (`thanks_heading(name)`, `error_message(text)`). They hold NO assertions.
- Assertions live in the test with `expect(locator).to_be_visible()`. `expect` auto-retries.
- No `time.sleep` and no `wait_for_timeout`. Wait on a visible locator instead.
- Keep UI tests to critical journeys; use API tests for everything else.
