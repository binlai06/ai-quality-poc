# AI Quality POC

[![PR checks](https://github.com/binlai06/ai-quality-poc/actions/workflows/pr.yml/badge.svg)](https://github.com/binlai06/ai-quality-poc/actions/workflows/pr.yml) [![Main checks](https://github.com/binlai06/ai-quality-poc/actions/workflows/main.yml/badge.svg)](https://github.com/binlai06/ai-quality-poc/actions/workflows/main.yml)

A proof of concept for **multi-agent quality engineering**: one **Head of Quality** agent coordinates specialist sub-agents to test a real web application end to end. You talk to the Head of Quality only; it plans, delegates, re-runs the checks itself and reports.

The application under test is the [Restful Booker Platform](https://github.com/mwinteringham/restful-booker-platform) (RBP), a hotel booking demo with REST services and a React UI. It contains intentional bugs, which this project finds, reports and tracks.

> **Status:** API and UI test frameworks are done. Five agents work: Head of Quality, Test Design, BE Automation, FE Automation (with the Playwright MCP) and GitHub Issues. Two stories are covered end to end (BOOK-1 and BOOK-2), a script checks that every story has a passing test, guardrails protect `main`, and a release gate script computes the release verdict. CI runs on GitHub Actions: lint and unit tests on every pull request, and on every push to `main` the full suite against RBP built in the runner, plus the release gate. Next: rehearsals and the live demo.

## Summary

| | |
|---|---|
| Current result | **106 passed, 21 expected failures (known bugs)**, 1 race test excluded (72 API and UI tests plus 34 unit tests of the release gate) |
| Stories covered | BOOK-1 "As a guest, I can book a room"; BOOK-2 "As a guest, I can check which rooms are available for my dates" |
| Agents | Head of Quality, Test Design, BE Automation, FE Automation, GitHub Issues |
| Bugs found | #1, #2, #3, #4, #7, #8 (all tracked as GitHub issues and strict xfail tests) |
| Release verdict | `ci/release_gate.py` (script, not the LLM): four gates, verdict BLOCKED, APPROVED_WITH_KNOWN_RISKS or APPROVED; latest report in `docs/reports/` |
| Guardrails | GitHub ruleset on `main` (pull request required, no force push) plus `.claude/settings.json` |
| CI | GitHub Actions: `pr.yml` (lint and unit tests on every pull request), `main.yml` (RBP built in the runner at a pinned commit, warm-up run, full suite, release gate) |
| Next | Rehearsals and the demo |

## What is in the repo

| Layer | Tooling | Where |
|---|---|---|
| API tests | Python, pytest, requests, pydantic, Faker | `tests/api/`, `framework/api/`, `framework/models/`, `framework/factories/` |
| UI tests | Playwright for Python, Page Object Model | `tests/ui/`, `framework/pages/` |
| Unit tests of our own scripts | pytest, no RBP needed (marker `unit`) | `tests/unit/` |
| Test data cleanup | cleanup classes for rooms, messages and bookings | `framework/cleanup.py` |
| Story traceability | `docs/stories.md` and a checker script | `scripts/check_story_traceability.py` |
| Plans and reports | test condition matrices, probe records, release readiness reports | `docs/reports/` |
| Release gate | gates for lint, tests, traceability and leaks, with 34 unit tests | `ci/release_gate.py`, `tests/unit/test_release_gate.py` |
| Guardrails | permission rules (deny and ask), auto mode disabled | `.claude/settings.json` |
| Configuration | environment variables with local defaults | `framework/config.py` |
| Lint | ruff (markdown files excluded) | `ruff.toml` |
| Rules for humans and agents | `CLAUDE.md` and the skill `test-writing-conventions` | repo root, `.claude/skills/` |
| Agents | Claude Code sub-agents | `.claude/agents/` |

Services covered: authentication, rooms, messages and bookings (API), plus the home page, admin login, contact form, booking journey and availability search (UI).

## Architecture

```
Test  ->  Page Object / API client  ->  Playwright / requests  ->  RBP (Docker)
            ^
            Factories (data) + cleanup classes (tidy-up)
```

How the agents work together (demo stories "As a guest, I can book a room" and "As a guest, I can check which rooms are available for my dates"):

```
You -> Head of Quality: plan, wait for approval
    -> Test Design: test condition matrix, you choose the cases
    -> BE Automation: probe the app with curl, write and run API tests (own branch)
    -> FE Automation: explore the UI with the Playwright MCP, write UI tests (own branch)
    -> Head of Quality re-runs lint, the whole suite, the traceability check and the leak checks
    -> you review the diff and commit; a draft pull request is the review point

Failures and bugs:
You -> Head of Quality -> GitHub Issues: rerun a failure three times, classify it (bug, flaky, test problem),
       reproduce with curl, look for duplicates, draft the issue; it files or comments only with your quoted approval

Release readiness:
Head of Quality runs ci/release_gate.py, quotes the table and the exit code, explains it in plain words
    -> writes docs/reports/release-readiness-<date>.md; a human signs off
```

Next sub-agent: CI/CD (GitHub Actions).

## Test strategy

- **Test pyramid:** many fast API tests, a few UI tests for critical journeys only.
- **Arrange - Act - Assert:** set up in a fixture, one single action, then assert status, schema and business rules.
- **Independent tests:** every test creates its own data (unique `qa` names), cleans up even when it fails, and is safe to run in parallel.
- **No hard-coded data or URLs:** everything comes from factories and configuration.
- **Boundary testing:** limits are tested just outside the allowed range, with readable parametrized cases.
- **Known bugs stay visible:** a test asserts the correct behaviour and is marked `xfail(strict=True)` with the issue number. When the bug is fixed the suite turns red, which tells us to remove the marker.
- **Requirements coverage, not code coverage:** each test carries `story("<id>")`; the traceability script fails when a story has no passing test.
- **Tests must be able to fail:** new tests are checked by breaking the code under test on purpose (skip the click, empty answer, aborted request).
- **Test the cause at the cheapest layer:** for example a malformed date is tested at the service, not through the slow proxy.

Current result: **106 passed, 21 expected failures (known bugs)**. One booking test is occasionally flaky on the first run after a quiet period, so a warm-up run comes first and is reported, not hidden.

## Known application bugs found

| Issue | Summary |
|---|---|
| [#1](https://github.com/binlai06/ai-quality-poc/issues/1) | Login through the UI proxy returns 500 instead of 400 for a malformed body |
| [#2](https://github.com/binlai06/ai-quality-poc/issues/2) | The proxy route `/api/room/{id}` always returns 500, so the reservation page is blank |
| [#3](https://github.com/binlai06/ai-quality-poc/issues/3) | Creating a room through the proxy with an invalid token returns 500 |
| [#4](https://github.com/binlai06/ai-quality-poc/issues/4) | The room service returns 500 instead of 404 for an unknown room id |
| [#7](https://github.com/binlai06/ai-quality-poc/issues/7) | The availability endpoints list a room as unavailable only when a booking lies fully inside the searched range, although partial overlaps are rejected at booking time |
| [#8](https://github.com/binlai06/ai-quality-poc/issues/8) | The booking service returns 500 instead of 400 for a missing `bookingdates` and for malformed dates; the room search takes about 31 s through the proxy |

## Run it locally

Prerequisites: Docker Desktop, Python 3.12, git.

```bash
# 1. Start RBP (in its own folder, see the RBP repository for the build steps)
docker compose up -d

# 2. Set up this project
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# 3. Run the tests
pytest -m smoke                 # fast checks
pytest -n auto -m "not race"    # everything, in parallel (106 passed, 21 xfailed)
ruff check . && ruff format --check .   # lint
python scripts/check_story_traceability.py   # every story has a passing test
python ci/release_gate.py       # release verdict (exit 0, 1 or 2); --blocking-issues N,M blocks on known bugs
```

Against the public demo site instead of a local install:

```bash
RBP_BASE_URL=https://automationintesting.online pytest -m "not service and not race"
```

Settings (all optional): `RBP_BASE_URL`, `RBP_ROOM_URL`, `RBP_MESSAGE_URL`, `RBP_BOOKING_URL`, `RBP_TIMEOUT`, `RBP_ADMIN_USERNAME`, `RBP_ADMIN_PASSWORD`.

## Run the agents

With RBP running and the virtual environment set up, from the repo root:

```bash
claude --agent head-of-quality --add-dir <path to restful-booker-platform>
```

Then describe a user story and its limits. The Head of Quality presents a plan and waits for your approval before delegating.

The FE Automation agent explores the real UI with the Playwright MCP server. Register it once, in the repo folder (it is registered per project folder):

```bash
claude mcp add playwright -- npx @playwright/mcp@latest --isolated   # needs Node 18+
claude mcp list                                                         # check it is connected
```

Agents work on `quality/<topic>` branches. A human commits, opens a draft pull request, reviews the diff and merges.

## How the agents are governed

- The Head of Quality **coordinates and verifies**; it never edits code or tests. Its only write permission is for plans and reports under `docs/reports/`. Sub-agents do the work with the minimum tools they need, listed one by one (the Playwright MCP agent gets named tools only; the GitHub Issues agent has no edit tools).
- **Tiered, risk-based autonomy:** writing files on a working branch is low risk, pushing branches and opening draft pull requests is notified, and merges, CI changes and changes to assertions need a human.
- **Defence in depth:** a GitHub ruleset on `main` (pull request required, no force push, no deletion, no bypass); `.claude/settings.json` denies pushes to `main`, force pushes, merges, closing or deleting issues and edits of the application under test, and asks before other pushes, issue changes and edits of agents, settings, CI and `CLAUDE.md`; auto mode is disabled; each agent has its own tool list. Known limit: command rules match the command text, which is why the ruleset exists too.
- **Issues:** an agent never closes or edits an issue, and it files or comments only when the user's approval of the exact text is quoted in its task message. It reads the existing comments first, so it does not post twice.
- **Release verdict:** computed by `ci/release_gate.py`, not by the LLM, so it is reproducible. The Head of Quality runs it, quotes the result and explains it; a human signs off.
- Every agent is tested with a golden task, and its definition is fixed (with human approval) after a real failure.

## Roadmap

1. Foundations (done)
2. API and UI frameworks, including the booking service (done)
3. Head of Quality and sub-agents (done: Head of Quality, Test Design, BE Automation, FE Automation, GitHub Issues)
4. Guardrails and release gate (done), CI with GitHub Actions (done; Jenkins only if time allows), rehearsals, final demo

## Credits

Application under test: [Restful Booker Platform](https://github.com/mwinteringham/restful-booker-platform) by Mark Winteringham. This project is a learning and demonstration exercise.
