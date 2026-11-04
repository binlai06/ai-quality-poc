# CLAUDE.md — AI Quality POC

This file is the project's constitution. Every agent working in this repo reads it first and follows it.

## Purpose
A multi-agent quality system for the **Restful Booker Platform (RBP)**. The user talks only to the
**Head of Quality** agent, which plans the work, delegates it to specialist sub-agents in `.claude/agents/`,
reviews what they produce and reports back. This repo is a demo POC, so it must stay clean, readable
and explainable.

## Application under test
- Source (read-only, never modify): `~/personal/restful-booker-platform`
- Run locally: `docker compose up -d` from the RBP folder (Docker Desktop must be running)
- UI: http://localhost. Admin: http://localhost/admin (admin / password)
- Service ports: booking 3000, room 3001, branding 3002, auth 3004, report 3005, message 3006, UI 80
- Backup environment: https://automationintesting.online (resets every 10 minutes)
- RBP contains intentional bugs. Report them as GitHub issues; never work around them silently.

## Tech stack
- Python 3.12, virtual environment in `.venv`
- API tests: pytest + requests + pydantic (response models) + faker (test data)
- UI tests: Playwright for Python with the Page Object Model
- Lint/format: ruff
- CI: GitHub Actions (`.github/workflows/`) and a Jenkinsfile running on Jenkins in Docker (`ci/`)
- Tracking: GitHub Issues on binlai06/ai-quality-poc

## Repository layout
~~~
framework/            reusable test framework code (no tests here)
  config.py           settings read from environment variables, with local defaults
  api/                API clients, one class per RBP service, all extending BaseClient
  models/             pydantic models for requests and responses
  pages/              Playwright Page Objects and components
tests/
  api/                API tests (the bulk of the suite)
  ui/                 E2E UI tests (critical journeys only)
  conftest.py         shared fixtures
docs/                 test strategy, test cases, run reports
docker/               Dockerfiles / compose for the test runner and Jenkins
ci/                   Jenkinsfile and CI helpers
.claude/agents/       sub-agent definitions
~~~

## Engineering standards
- **OOP**: tests never call `requests` directly; they use API client classes. UI tests never use raw
  selectors; they use Page Objects.
- **Test pyramid**: favour API tests. Add a UI test only for a critical user journey that an API test
  cannot cover.
- **Independent tests**: each test creates its own data (factories/fixtures) and cleans up after itself.
  No test depends on another test or on run order. Tests must be safe to run in parallel.
- **Arrange – Act – Assert (AAA)**: every test has three parts, in this order. Arrange: set up
  data and state, usually through fixtures. Act: one single call to the system under test.
  Assert: check status code, schema and business rules. One Act per test. Separate the parts
  with blank lines, and add "# Arrange / # Act / # Assert" comments only when the test is long.
- **No hard-coded data or URLs**: URLs come from `framework/config.py`; data comes from factories.
- **Assertions**: check status code, response schema (pydantic) and business rules. One behaviour per test.
- **Markers**: every test has a layer marker (`api` or `ui`) and a suite marker (`smoke` or `regression`).
  Link tests to their story or bug with `@pytest.mark.issue("<number>")` when one exists.
- **Naming**: `test_<behaviour>_<expected_result>`, e.g. `test_create_room_with_valid_data_returns_201`.
- **Readability**: type hints, short functions, docstrings on public classes. No commented-out code.

## Commands
~~~bash
source .venv/bin/activate          # activate the virtual environment
pytest -m smoke                    # fast checks
pytest -m "api and regression"     # full API regression
pytest -n auto                     # run in parallel
ruff check . && ruff format .      # lint and format
~~~

## Working rules for agents
1. **Propose, then act.** Present a short plan and wait for the user's approval before writing files,
   committing, pushing or creating GitHub issues.
2. Run the relevant tests after every change and report the real result. Never claim a test passes
   without running it.
3. Keep changes small and focused, one concern per commit.
4. Commit messages follow Conventional Commits: `feat:`, `fix:`, `test:`, `ci:`, `docs:`, `chore:`, `refactor:`.
5. Never modify the RBP source, never commit secrets, and never push without the user's approval.
6. When a test fails, decide whether it's a test problem or an application bug. Explain why, then propose
   a fix or a bug report.
7. Explain decisions in plain language. The user is learning and will present this work in an interview.
