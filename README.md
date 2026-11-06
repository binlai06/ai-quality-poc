# AI Quality POC

A proof of concept for **multi-agent quality engineering**: one **Head of Quality** agent coordinates specialist sub-agents (test design, backend automation, frontend automation, bug management, reporting, CI/CD) to test a real web application end to end.

The application under test is the [Restful Booker Platform](https://github.com/mwinteringham/restful-booker-platform) (RBP), a hotel booking demo with REST services and a React UI. It contains intentional bugs, which this project finds, reports and tracks.

> **Status:** the test frameworks (API and UI) are done. The agents are being built (Week 3), then CI/CD and the live demo (Week 4).

## What is in the repo

| Layer | Tooling | Where |
|---|---|---|
| API tests | Python, pytest, requests, pydantic, Faker | `tests/api/`, `framework/api/`, `framework/models/`, `framework/factories/` |
| UI tests | Playwright for Python, Page Object Model | `tests/ui/`, `framework/pages/` |
| Configuration | environment variables with local defaults | `framework/config.py` |
| Rules for humans and agents | `CLAUDE.md` | repo root |
| Agents (in progress) | Claude Code sub-agents | `.claude/agents/` |

## Architecture

```
Test  ->  Page Object / API client  ->  Playwright / requests  ->  RBP (Docker)
            ^
            Factories (data) + cleanup classes (tidy-up)
```

Planned agent flow for the demo story "As a guest, I can book a room":

```
Story -> Head of Quality -> Test Design -> BE + FE Automation (own branch)
      -> Head of Quality re-runs tests and checks gates
      -> Bug Management (GitHub Issues) -> Reporting -> human sign-off
```

## Test strategy

- **Test pyramid:** many fast API tests, a few UI tests for critical journeys only.
- **Arrange - Act - Assert:** set up in a fixture, one single action, then assert status, schema and business rules.
- **Independent tests:** every test creates its own data (unique `qa-` names), cleans up even when it fails, and is safe to run in parallel.
- **No hard-coded data or URLs:** everything comes from factories and configuration.
- **Known bugs stay visible:** a test asserts the correct behaviour and is marked `xfail(strict=True)` with the issue number. When the bug is fixed the suite turns red, which tells us to remove the marker.

## Known application bugs found

| Issue | Summary |
|---|---|
| [#1](https://github.com/binlai06/ai-quality-poc/issues/1) | Login through the UI proxy returns 500 instead of 400 for a malformed body |
| [#2](https://github.com/binlai06/ai-quality-poc/issues/2) | The proxy route `/api/room/{id}` always returns 500, so the reservation page is blank |
| [#3](https://github.com/binlai06/ai-quality-poc/issues/3) | Creating a room through the proxy with an invalid token returns 500 |
| [#4](https://github.com/binlai06/ai-quality-poc/issues/4) | The room service returns 500 instead of 404 for an unknown room id |

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
pytest -n auto -m "not race"    # everything, in parallel
```

Against the public demo site instead of a local install:

```bash
RBP_BASE_URL=https://automationintesting.online pytest -m "not service and not race"
```

Settings (all optional): `RBP_BASE_URL`, `RBP_ROOM_URL`, `RBP_MESSAGE_URL`, `RBP_TIMEOUT`, `RBP_ADMIN_USERNAME`, `RBP_ADMIN_PASSWORD`.

## How the agents are governed

- The Head of Quality **coordinates and verifies**; sub-agents do the work with the minimum tools they need.
- **Tiered, risk-based autonomy:** writing files on a working branch is free, pushing branches and opening draft pull requests is notified, and merges, CI changes and changes to assertions need a human.
- Autonomy is introduced step by step as the agents prove themselves.

## Roadmap

1. Foundations (done)
2. API and UI frameworks (done)
3. Head of Quality and sub-agents (in progress)
4. CI/CD with GitHub Actions and Jenkins, reporting, final demo

## Credits

Application under test: [Restful Booker Platform](https://github.com/mwinteringham/restful-booker-platform) by Mark Winteringham. This project is a learning and demonstration exercise.
