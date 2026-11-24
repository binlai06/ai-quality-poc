# Release readiness — BOOK-1, BOOK-2 — 2026-11-24

Command: `.venv/bin/python ci/release_gate.py --json docs/reports/release-verdict.json --blocking-issues 2`

## Verdict

```
Verdict: BLOCKED
  - blocking issue #2
```

Exit code: **1**

## Gate table (word for word from the script)

```
Release gate

gate          result  reason
lint          PASS    ruff check and ruff format are clean
tests         PASS    106 passed, 21 xfailed
traceability  PASS    every story has a passing test
leaks         PASS    no leftover qa- data
```

## Warm-up run, not used for the verdict

`======================= 106 passed, 21 xfailed in 10.50s =======================`

## Known bugs (from release-verdict.json and marker grep)

| Issue | Stories (from the JSON) | What it means |
|---|---|---|
| #1 | none | auth test xfail |
| #2 | none | Proxy PUT/DELETE `/api/room/{id}` returns 500; UI reservation page blank. **Blocking, named by the user.** |
| #3 | none | proxy room xfail |
| #4 | none | GET of unknown or deleted room returns 500 instead of 404 |
| #7 | BOOK-1, BOOK-2 | Unavailable-rooms search misses partly overlapping bookings; the UI still lists a booked room |
| #8 | BOOK-1, BOOK-2 | Malformed requests return 500 instead of 400 |

Note: `tests/api/test_rooms.py` has a race test marked `issue("D")`, which is not a numeric issue. It is excluded by `-m "not race"`. Please check it.

## Decisions for the user

1. Issue #2 blocks the release. Fix it, or remove it from the blocking list.
2. Are #7 and #8 acceptable for release? Both touch BOOK-1 and BOOK-2. The script did not block on them.
3. Fix the non-numeric `issue("D")` marker. This is a request to you; I do not edit tests.
4. The gate test run was a single run. I did no extra reruns, because no test gate failed.
