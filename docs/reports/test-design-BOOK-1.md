# Test design: BOOK-1 "As a guest, I can book a room"

- Service: booking, port 3000 (`/booking`)
- Produced by: test-design agent (read-only, from source). Reviewed by the Head of Quality.
- Status: matrix approved for saving. Automation scope NOT yet chosen. Stage 1 (curl probe) pending.
- Every expected result below is a **hypothesis** from reading the RBP source. Verify with curl before asserting.

## Validation rules seen in source

| Field | Rule |
|---|---|
| `roomid` | `@Min(1)` |
| `firstname` | not blank, size 3-18 |
| `lastname` | not blank, size 3-30 |
| `email` | optional, `@NotEmpty @Email` |
| `phone` | optional, `@NotEmpty`, size 11-21 |
| `bookingdates.checkin`, `.checkout` | `@NotNull` each |
| Date logic | `checkin < checkout` required (`DateCheckValidator`), otherwise 409 |
| Conflict check | `BookingDB.java:32`, `142-173`. Any conflict returns 409 |

Existing tests (`tests/api/test_booking_service.py`, 4 functions, 8 collected items):
- T1 = `test_get_booking_summary_for_room_without_bookings_returns_200_and_empty_list`
- T2 = `test_check_unavailable_rooms_for_future_stay_returns_200_and_room_list`
- T3 = `test_create_booking_for_existing_room_returns_201_and_appears_in_room_summary`
- T4 = `test_create_booking_with_invalid_field_returns_400_and_creates_nothing` with ids `malformed-email`, `firstname-too-short`, `lastname-too-short`, `firstname-too-long`, `phone-too-short`

All rows are API layer. The UI journey already exists in `tests/ui/test_booking.py`.

## Area A: create a booking (POST /booking/)

| ID | Condition | Input / change | Expected (hypothesis) | Suite / Prio | Status, covered by |
|---|---|---|---|---|---|
| A01 | Happy path | Valid guest, existing room, future stay | 201, body `{bookingid, booking{...}}` validates as `CreatedBooking`; email and phone not echoed | smoke / P1 | COVERED: T3 (marked regression today; mixes create and summary) |
| A02 | Malformed email | `email="not-an-email"` | 400, `fieldErrors == ["must be a well-formed email address"]`, nothing created | regression / P2 | COVERED: T4 `malformed-email` |
| A03 | Firstname below min | 2 chars | 400, "size must be between 3 and 18" | regression / P2 | COVERED: T4 `firstname-too-short` |
| A04 | Firstname above max | 19 chars | 400, same message | regression / P2 | COVERED: T4 `firstname-too-long` |
| A05 | Firstname at min edge | 3 chars | 201 | regression / P2 | GAP |
| A06 | Firstname at max edge | 18 chars | 201 | regression / P2 | GAP |
| A07 | Lastname below min | 2 chars | 400, "size must be between 3 and 30" | regression / P2 | COVERED: T4 `lastname-too-short` |
| A08 | Lastname at min edge | 3 chars | 201 | regression / P3 | GAP |
| A09 | Lastname at max edge | 30 chars | 201 | regression / P3 | GAP |
| A10 | Lastname above max | 31 chars | 400, "size must be between 3 and 30" | regression / P2 | GAP |
| A11 | Phone below min | 10 digits | 400, "size must be between 11 and 21" | regression / P2 | COVERED: T4 `phone-too-short` |
| A12 | Phone at min edge | 11 chars | 201 (implicit in T3, not asserted on purpose) | regression / P3 | GAP (implicit in T3) |
| A13 | Phone at max edge | 21 chars | 201 | regression / P3 | GAP |
| A14 | Phone above max | 22 chars | 400 | regression / P2 | GAP |
| A15 | Blank names | `firstname=""` or whitespace | 400, likely two messages; assertion must tolerate order | regression / P3 | GAP |
| A16 | Room id below min | `roomid=0`, negative | 400, message about "greater than or equal to 1" | regression / P2 | GAP |
| A17 | Email and phone omitted | Fields absent | 201, no "new booking" message sent (`BookingService.java:112`) | regression / P2 | GAP |
| A18 | Email empty string | `email=""` | 400 (`@NotEmpty`) | regression / P3 | GAP |
| A19 | Checkin equals checkout | Same date | 409, no body | regression / P1 | GAP |
| A20 | Checkout before checkin | Dates reversed | 409 | regression / P1 | GAP |
| A21 | Duplicate stay, same room | Same dates as existing booking | 409, existing booking unchanged | regression / P1 | GAP |
| A22 | Partial overlap, same room | New stay overlaps start or end of existing | 409 | regression / P1 | GAP |
| A23 | Back-to-back stay (boundary) | New checkin equals existing checkout | 201 (query shifts checkin +1 day, `BookingDB.java:145-147`) | regression / P2 | GAP |
| A24 | Same dates, different room | Another room | 201 | regression / P2 | GAP |
| A25 | Null date | `checkin: null` | 400 (`@NotNull`) | regression / P2 | GAP |
| A26 | Malformed date | `"2026-13-45"` | 400 (JSON parse failure) | regression / P3 | GAP |
| A27 | Missing `bookingdates` object | Object absent | Suspected 500 (`@Valid` on null passes, `DateCheckValidator` dereferences null). Suspected app bug, to verify with curl | regression / P2 | GAP |
| A28 | Unknown room id | `roomid=<non-existent>` | Probably 201, no room existence check visible. OPEN QUESTION, not asserted | regression / P2 | GAP (open question) |
| A29 | Empty or invalid JSON body | `{}` or garbage | 400 | regression / P3 | GAP |
| A30 | `depositpaid` false | `false` | 201 | regression / P3 | GAP |
| A31 | Past dates | Stay in the past | Unclear, no past-date rule in source. OPEN QUESTION, not asserted | regression / P3 | GAP (open question) |
| A32 | Side effect: message created | After successful create | "You have a new booking!" message exists (message service; cleanup-sensitive) | regression / P2 | GAP |

## Area B: room booking summary (GET /booking/summary?roomid=)

| ID | Condition | Input / change | Expected (hypothesis) | Suite / Prio | Status, covered by |
|---|---|---|---|---|---|
| B01 | Room with no bookings | Random unused id | 200, `{"bookings": []}` | smoke / P1 | COVERED: T1 |
| B02 | Room with one booking | After create | 200, one entry with matching dates | smoke / P1 | COVERED (partial): T3, second assertion inside create test |
| B03 | Room with two bookings | Two non-overlapping stays | 200, both listed | regression / P2 | GAP |
| B04 | Only date ranges exposed | Inspect item | Only `bookingDates`; no name, email or phone | regression / P2 | GAP |
| B05 | Missing `roomid` | No param | 400 | regression / P2 | GAP |
| B06 | Non-numeric `roomid` | `roomid=abc` | Suspected 500 (id concatenated into SQL, `BookingDB.java:189`). Suspected app bug, to verify with curl (status code only; no injection) | regression / P2 | GAP |
| B07 | Boundary ids | `0`, `-1` | 200, empty list | regression / P3 | GAP |
| B08 | Isolation between rooms | Booking in room X, query room Y | Y returns `[]` | regression / P2 | GAP |

## Area C: unavailable rooms (GET /booking/unavailable?checkin=&checkout=)

Filter in source: `checkin >= :from AND checkout <= :to` (`BookingDB.java:201`). Do not assert on list length; assert on your own room id only.

| ID | Condition | Input / change | Expected (hypothesis) | Suite / Prio | Status, covered by |
|---|---|---|---|---|---|
| C01 | Range with no matching booking | Future range | 200, items validate as `UnavailableRoom`, unique room ids | smoke / P1 | COVERED: T2 (shape only, no business rule) |
| C02 | Booking fully inside range | Booking 12-14, query 10-20 | 200, own roomid present | smoke / P1 | GAP |
| C03 | Booking exactly equals range | Booking 10-15, query 10-15 | Own roomid present | regression / P2 | GAP |
| C04 | Booking outside range | Booking 30-32, query 10-15 | Own roomid absent | regression / P2 | GAP |
| C05 | Partial overlap at start of booking | Booking 08-12, query 10-15 | Business intent: listed. By source: NOT listed. **Suspected app bug, to verify with curl** | regression / P1 | GAP |
| C06 | Partial overlap at end of booking | Booking 13-18, query 10-15 | Same as C05. **Suspected app bug, to verify with curl** | regression / P1 | GAP |
| C07 | Booking encloses the range | Booking 05-20, query 10-15 | Same as C05. **Suspected app bug, to verify with curl** | regression / P1 | GAP |
| C08 | One-day boundary | Booking checkin = range checkin minus 1 day | Same as C05. **Suspected app bug, to verify with curl** | regression / P2 | GAP |
| C09 | Dedup | Two bookings of same room inside range | Room appears once (`BookingDB.java:208-220`) | regression / P3 | GAP |
| C10 | Missing params | No checkin or checkout | 400 | regression / P2 | GAP |
| C11 | Malformed date | `checkin=abc` | Suspected 500 (`LocalDate.parse` unhandled, `BookingController.java:32`). Suspected app bug, to verify with curl | regression / P2 | GAP |
| C12 | Reversed range | checkout before checkin | 200, empty list | regression / P3 | GAP |
| C13 | Same-day range | checkin equals checkout | Ambiguous. OPEN QUESTION, not asserted | regression / P3 | GAP (open question) |

## Coverage summary

| Area | Rows | COVERED | GAP |
|---|---|---|---|
| A create | 32 | 6 (A01, A02, A03, A04, A07, A11) | 26 |
| B summary | 8 | 2 (B01, B02) | 6 |
| C unavailable | 13 | 1 (C01) | 12 |
| Total | 53 | 9 | 44 |

## Existing 8 collected tests and the rows they cover

| # | Collected test | Rows |
|---|---|---|
| 1 | `test_get_booking_summary_for_room_without_bookings_returns_200_and_empty_list` | B01 |
| 2 | `test_check_unavailable_rooms_for_future_stay_returns_200_and_room_list` | C01 |
| 3 | `test_create_booking_for_existing_room_returns_201_and_appears_in_room_summary` | A01, B02 |
| 4 | `..._and_creates_nothing[malformed-email]` | A02 |
| 5 | `..._and_creates_nothing[firstname-too-short]` | A03 |
| 6 | `..._and_creates_nothing[lastname-too-short]` | A07 |
| 7 | `..._and_creates_nothing[firstname-too-long]` | A04 |
| 8 | `..._and_creates_nothing[phone-too-short]` | A11 |

Quality notes: T3 holds two behaviours (create and summary); T2 would pass even if the endpoint always returned `[]`; A01 is the critical path but is marked regression.

## Suspected application bugs (to verify with curl, nothing filed)

1. **C05-C08: unavailable-rooms query misses partial overlaps.** `BookingDB.java:201` returns only bookings fully inside the requested range. For range 10-15, bookings 08-12, 13-18, 05-20 and 09-11 are missed. The create-conflict query at `BookingDB.java:32` handles partial overlaps, so the two endpoints disagree for the same dates.
2. **A27:** missing `bookingdates` probably returns 500 instead of 400 (`Booking.java:40-41`, `DateCheckValidator.java:10`).
3. **B06:** non-numeric `roomid` on summary probably returns 500; id is concatenated into SQL (`BookingDB.java:85`, `189`). Status-code check only; no injection attempts.
4. **C11:** malformed date on unavailable probably returns 500 (`BookingController.java:32`).

## Open questions (not asserted)

- A28: should a booking for an unknown room id be rejected?
- A31: should past dates be rejected?
- C13: what should a same-day range return on the unavailable endpoint?
- Unavailable-rooms semantics: if "fully contained only" is intended, C05-C08 are not bugs.
- A23: is a back-to-back stay allowed (assumed yes)?

## Notes for automation

- Unavailable-rooms tests share one global list. Use distinctive date ranges (e.g. `days_ahead` 400 or more) and assert only on the test's own room id.
- Overlap rows (C02-C08, A21-A24, B03) need a booking helper that sets exact dates and accepts two bookings in one room, with `booking_cleanup` tracking both. This is framework work for be-automation.
- Any created booking also creates a message in the message service; the cleanup fixture handles this.
- xfail pattern for confirmed bugs: `issue(<n>)` + `xfail(strict=True, raises=AssertionError)`. Changing xfail markers needs user approval.
