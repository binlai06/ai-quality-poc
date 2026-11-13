# Probe record BOOK-2: "Check which rooms are available for my dates"

- Story: BOOK-2, home page http://localhost, section "Check Availability & Book Your Stay"
- Probe A and B: exploration with the Playwright MCP browser (fe-automation). Probe C: API only, curl (be-automation).
- No tests, no files edited and no data left behind by any probe.
- Status: Probe A done. Probe B incomplete (browser tab died), UI retry not planned. Probe C done.

## Probe A: facts (from an earlier session, reported by the user)
- Two plain text boxes, Check In and Check Out, format DD/MM/YYYY. Defaults: today and tomorrow. Button "Check Availability".
- The boxes have no accessible name. Locators that worked: `getByRole('textbox').first()` (Check In) and `.nth(1)` (Check Out).
- Valid search 20/12/2026 to 22/12/2026:
  - all 3 rooms stay listed (Single, Double, Suite), no message, URL stays http://localhost/
  - request: `GET /api/room?checkin=2026-12-20&checkout=2026-12-22`, ISO dates, status 200
  - "Book now" links get `?checkin=...&checkout=...` added
  - console: 0 errors
- Observations only (not confirmed bugs): all three room images have the alt text "Single Room"; a valid search gives no feedback to the guest.

## Probe B: what was observed (fe-automation report, not independently reproduced)
- Page load works. "Check Availability" with the default dates (13/11/2026 to 14/11/2026) works; the page stays alive, 3 rooms listed, "Book now" hrefs unchanged (`checkin=2026-11-13&checkout=2026-11-14`).
- New fact: filling the Check In box opens a "Choose Date" datepicker dialog (December 2026 shown after typing 22/12/2026, with gridcells).
- The MCP browser tab died after the second box was filled, while the datepicker was open. 4 of 4 attempts, valid and invalid dates alike, so the invalid range is not the cause.
- Network and console logs read empty every time, because the browser context was recreated. No request or console error could be checked.
- Cause of the tab death: unknown. Not an application finding. Possibly a limit of the MCP browser; an app crash is not excluded but there is no evidence for it (Probe A filled both boxes without the problem).
- The agent stopped after 3 failed attempts on one step, as the rules say. Turn count reported about 29; the run shows 59 tool uses, so the count is unverified.
- Checks by the Head of Quality after the probe: `git status --short` empty; the three leak checks printed nothing.

### Not checked (Probe B)
- Case (a): check-out before check-in. UI shown, blocked or let through, request, status.
- Case (b): both boxes empty.
- Case (c): only one box empty.
- Case (d): non-date text such as "abc".
- Console and network behaviour for all four cases.
- Keyboard handling of the datepicker; closing it with Escape.
- Request payloads for invalid input.
- A search over an existing booking in the UI (stage 2).
- The alt text and the missing feedback were not investigated further.

## Probe C: API availability query with a booking (be-automation, curl only)
Setup: one throwaway room `qa-room-3ff1e232` (id 4) and one booking id 4 from 2031-03-10 to 2031-03-15. Both endpoints queried for each case. "Present" means the room id appears in the returned room list. Everything was deleted afterwards (booking, its auto-created message, room). The Head of Quality re-ran `git status --short` (only this file untracked) and the three leak checks (all empty).

| case | range (checkin to checkout) | proxy `GET /api/room` | service `GET :3001/room/` | room present |
|---|---|---|---|---|
| a. control, no booking | 2031-06-01 to 2031-06-05 | 200 | 200 | yes |
| b. range contains the booking | 2031-03-01 to 2031-03-20 | 200 | 200 | no (hidden) |
| c. overlaps the start only | 2031-03-05 to 2031-03-12 | 200 | 200 | yes |
| d. overlaps the end only | 2031-03-12 to 2031-03-20 | 200 | 200 | yes |
| e. inside the booking | 2031-03-11 to 2031-03-13 | 200 | 200 | yes |
| f. check-out before check-in | 2031-03-15 to 2031-03-10 | 200 | 200 | yes |
| g. `checkin=abc` | abc to 2031-03-10 | 500 | 500 | n/a |
| g2. `checkout=abc` (extra) | 2031-03-10 to abc | 500 | 500 | n/a |

- Proxy and service agree on every valid-date case (same status, same rooms). The room list had 4 rooms when the room was visible and 3 when hidden.
- Malformed date: both return 500 but the bodies differ. The proxy returns `[]`. The service returns a Spring error JSON (`status 500, error Internal Server Error, path /room/`).
- The booking service gives the same picture: `GET :3000/booking/unavailable` returned `[]` for case e and `[{"roomid":4}]` for case b (reported by the agent).
- The agent's first helper function failed to parse; the table comes from its second, clean run. The agent briefly wrote two temp files under /tmp and deleted them (checked: none left).

### Findings
1. **Booked room still listed on partial overlap and when the search is inside the booking (cases c, d, e).** Known bug **#7**. Source read by the Head of Quality: `booking/src/main/java/com/automationintesting/db/BookingDB.java:201` selects `WHERE checkin >= ? AND checkout <= ?`, so only a booking fully inside the searched range is reported as unavailable. The create-time conflict check (line 32) uses a proper overlap test, so the two checks disagree. Effect on the UI: a guest can be shown a room as free that a create call rejects with 409. The user comments on #7.
2. **Malformed date returns 500 (case g).** Same class as bug **#8** (500 instead of 400). Source: `BookingController.java:31` calls `LocalDate.parse(checkin)` without handling. The proxy hides the error as `[]`, so a failure looks like "no rooms". The user comments on #8.
3. **OPEN QUESTION, not a bug: check-out before check-in returns 200 with the full room list (case f).** Inferred: the two conditions in the query cannot both be true for a reversed range, so nothing matches and no validation exists. The intended behaviour is not defined, so no test is written for it until the user decides.
4. Side observation: `GET :3001/room/<deleted id>` returns 500, matching the known bug #4.

### Not checked (Probe C)
- Booking service code beyond the lines quoted above (the source was read only by the Head of Quality, for the query and the controller).
- Boundary dates: a search starting on the booking's check-out day, or ending on its check-in day.
- A second booking in the same room, bookings in other rooms, a missing parameter, a past date.
- The backup environment (automationintesting.online).

## Decisions
1. No retry of the UI probe. The facts above are recorded as they are.
2. Booked-room-still-listed is bug #7; malformed date 500 is bug #8. The user comments on both issues. No new issue.
3. Reversed dates (case f) stay an open question. No test.
4. Stage 2 for BOOK-2 has no new test-design matrix (the story is small):
   - A. API tests in `tests/api/test_room_availability.py`.
   - B. UI tests on the home page, after A is reviewed.
5. xfail markers approved by the user for exactly: the three partial-overlap and inside cases (issue 7), the malformed-date case (issue 8), and the UI search inside a booking (issue 7). Nothing else.
