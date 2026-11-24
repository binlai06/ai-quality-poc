"""Release gate: one deterministic verdict for a release candidate. No LLM involved.

Hard gates (lint, tests, story traceability, leak check) each pass or fail with a
short reason. Known bugs are read from the xfailed tests ("RBP bug #n" in the
xfail reason) together with their story markers. The verdict comes from a pure
function, `evaluate`.

Known bugs and XPASS(strict) are read with a small pytest plugin (this same file,
loaded with `-p release_gate`) that records every report to a JSON file in a
self-cleaning temporary directory.

Usage: python ci/release_gate.py [--blocking-issues 2,5] [--json PATH]
Exit code: 0 APPROVED or APPROVED_WITH_KNOWN_RISKS, 1 BLOCKED, 2 a gate could not run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import pytest
import requests

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from framework.config import settings

RESULTS_ENV = "RELEASE_GATE_RESULTS"
BUG_REASON = re.compile(r"RBP bug #(\d+)")
BAD_OUTCOMES = ("failed", "error", "xpass_strict")
LEAK_PATTERNS = (
    ("rooms", r'"roomName":"qa-room-[a-z0-9]*"'),
    ("message subjects", r"qa-subject-[a-z0-9]*"),
    ("message guests", r"qa[0-9a-f]{8} Guest[0-9a-f]{8}"),
)
EXIT_GATE_UNAVAILABLE = 2


class Verdict(str, Enum):
    """The three possible release verdicts."""

    APPROVED = "APPROVED"
    APPROVED_WITH_KNOWN_RISKS = "APPROVED_WITH_KNOWN_RISKS"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class Gate:
    """Result of one hard gate."""

    name: str
    passed: bool
    reason: str


@dataclass(frozen=True)
class KnownBug:
    """A known application bug (one GitHub issue) and the stories its xfailed tests touch.

    `issue` is None when an xfail reason does not name an issue.
    """

    issue: int | None
    stories: tuple[str, ...] = ()


@dataclass(frozen=True)
class Decision:
    """The verdict and the reasons behind it."""

    verdict: Verdict
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class TestRecord:
    """Outcome of one test: passed, failed, error, skipped, xfailed, xpassed or xpass_strict."""

    __test__ = False  # not a pytest test class

    nodeid: str
    outcome: str
    reason: str = ""
    stories: tuple[str, ...] = ()


class GateUnavailable(Exception):
    """A gate could not run at all (for example a tool is missing)."""


def _label(bug: KnownBug) -> str:
    stories = f" (stories: {', '.join(bug.stories)})" if bug.stories else ""
    return (
        f"known bug #{bug.issue}{stories}"
        if bug.issue
        else f"known bug without issue{stories}"
    )


def evaluate(
    gates: list[Gate],
    known_bugs: list[KnownBug],
    blocking_issues: frozenset[int],
) -> Decision:
    """Pure decision logic.

    BLOCKED when there is no gate, when a gate fails or when a known bug is a blocking issue.
    Otherwise APPROVED_WITH_KNOWN_RISKS when there is a known bug, else APPROVED.
    """
    if not gates:
        return Decision(Verdict.BLOCKED, ("no gates were evaluated",))
    reasons = [f"gate {g.name} failed: {g.reason}" for g in gates if not g.passed]
    blocking = sorted({b.issue for b in known_bugs if b.issue in blocking_issues})
    reasons += [f"blocking issue #{issue}" for issue in blocking]
    if reasons:
        return Decision(Verdict.BLOCKED, tuple(reasons))
    if known_bugs:
        return Decision(
            Verdict.APPROVED_WITH_KNOWN_RISKS, tuple(_label(b) for b in known_bugs)
        )
    return Decision(Verdict.APPROVED, ("all gates passed and no known bugs",))


def parse_blocking_issues(text: str) -> frozenset[int]:
    """Read a comma list such as "2,5" into issue numbers. Empty text means none."""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not all(p.isdigit() for p in parts):
        raise ValueError(
            f"blocking issues must be a comma list of numbers, got {text!r}"
        )
    return frozenset(int(p) for p in parts)


def exit_code(verdict: Verdict, gate_unavailable: bool) -> int:
    """0 approved (with or without risks), 1 blocked, 2 when a gate could not run."""
    if gate_unavailable:
        return EXIT_GATE_UNAVAILABLE
    return 1 if verdict is Verdict.BLOCKED else 0


def collect_known_bugs(records: list[TestRecord]) -> list[KnownBug]:
    """One KnownBug per issue number, with the sorted stories of its xfailed tests.

    An xfail whose reason names no issue becomes a single KnownBug with issue None.
    """
    stories: dict[int | None, set[str]] = {}
    for record in records:
        if record.outcome != "xfailed":
            continue
        match = BUG_REASON.search(record.reason)
        issue = int(match.group(1)) if match else None
        stories.setdefault(issue, set()).update(record.stories)
    ordered = sorted(stories, key=lambda i: (i is None, i or 0))
    return [KnownBug(issue, tuple(sorted(stories[issue]))) for issue in ordered]


def judge_tests_gate(records: list[TestRecord], returncode: int) -> Gate:
    """Pass when no test failed, errored or XPASSed a strict xfail, and pytest exited 0."""
    bad = [r for r in records if r.outcome in BAD_OUTCOMES]
    if bad:
        counts = ", ".join(
            f"{sum(r.outcome == o for r in bad)} {o.replace('_', ' ')}"
            for o in BAD_OUTCOMES
            if any(r.outcome == o for r in bad)
        )
        return Gate("tests", False, f"{counts} (first: {bad[0].nodeid})")
    if returncode != 0:
        return Gate("tests", False, f"pytest exited with code {returncode}")
    passed = sum(r.outcome == "passed" for r in records)
    xfailed = sum(r.outcome == "xfailed" for r in records)
    return Gate("tests", True, f"{passed} passed, {xfailed} xfailed")


def leaks_gate(bodies: dict[str, str]) -> Gate:
    """Pass when no leftover qa- test data is found. `bodies` maps "room"/"message" to a response body."""
    found = []
    for label, pattern in LEAK_PATTERNS:
        source = "room" if label == "rooms" else "message"
        matches = re.findall(pattern, bodies[source])
        if matches:
            found.append(f"{len(matches)} leaked {label}")
    if found:
        return Gate("leaks", False, ", ".join(found))
    return Gate("leaks", True, "no leftover qa- data")


def exit_status_gate(name: str, ok_reason: str, failed: list[str]) -> Gate:
    """Build a gate from the names of the commands that failed."""
    if failed:
        return Gate(name, False, f"{', '.join(failed)} failed")
    return Gate(name, True, ok_reason)


def format_table(gates: list[Gate], decision: Decision) -> str:
    """Render the gates and the verdict as a plain text table."""
    header = ("gate", "result", "reason")
    rows = [(g.name, "PASS" if g.passed else "FAIL", g.reason) for g in gates]
    table = [header, *rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    lines = [
        "  ".join(c.ljust(w) for c, w in zip(row, widths)).rstrip() for row in table
    ]
    lines.append("")
    lines.append(f"Verdict: {decision.verdict.value}")
    lines += [f"  - {reason}" for reason in decision.reasons]
    return "\n".join(lines)


def to_report(
    gates: list[Gate], known_bugs: list[KnownBug], decision: Decision
) -> dict:
    """The JSON document written by --json."""
    return {
        "verdict": decision.verdict.value,
        "reasons": list(decision.reasons),
        "gates": [
            {"name": g.name, "passed": g.passed, "reason": g.reason} for g in gates
        ],
        "known_bugs": [
            {"issue": b.issue, "stories": list(b.stories)} for b in known_bugs
        ],
    }


class _Recorder:
    """Pytest plugin for the controller process: keeps one record per test."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.records: dict[str, TestRecord] = {}

    def pytest_runtest_logreport(self, report) -> None:
        record = self._record(report)
        if record is None:
            return
        previous = self.records.get(record.nodeid)
        if (
            previous is None
            or previous.outcome not in BAD_OUTCOMES
            or (record.outcome in BAD_OUTCOMES)
        ):
            self.records[record.nodeid] = record

    @staticmethod
    def _record(report) -> TestRecord | None:
        stories = tuple(v for k, v in report.user_properties if k == "story")
        wasxfail = getattr(report, "wasxfail", None)
        if report.failed:
            strict = report.when == "call" and "XPASS(strict)" in str(report.longrepr)
            outcome = (
                "xpass_strict"
                if strict
                else "failed"
                if report.when == "call"
                else "error"
            )
            return TestRecord(report.nodeid, outcome, "", stories)
        if wasxfail is not None:
            if report.skipped:
                return TestRecord(report.nodeid, "xfailed", wasxfail, stories)
            return (
                TestRecord(report.nodeid, "xpassed", wasxfail, stories)
                if report.when == "call"
                else None
            )
        if report.when == "call":
            return TestRecord(
                report.nodeid, "skipped" if report.skipped else "passed", "", stories
            )
        if report.skipped:
            return TestRecord(report.nodeid, "skipped", "", stories)
        return None

    def pytest_sessionfinish(self) -> None:
        data = [r.__dict__ for r in self.records.values()]
        Path(self.path).write_text(json.dumps(data))


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    """Runs where the test runs (also in xdist workers): copy story markers onto the report."""
    report = yield
    for marker in item.iter_markers("story"):
        if marker.args:
            report.user_properties.append(("story", str(marker.args[0])))
    return report


def pytest_configure(config) -> None:
    """Register the recorder in the controller process when the results file is requested."""
    path = os.environ.get(RESULTS_ENV)
    if path and not hasattr(config, "workerinput"):
        config.pluginmanager.register(_Recorder(path))


def _run(command: list[str], **kwargs) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, cwd=REPO_ROOT, text=True, check=False, **kwargs)
    except OSError as error:
        raise GateUnavailable(f"cannot run {command[0]}: {error}") from error


def _ruff() -> str:
    candidate = Path(sys.executable).parent / "ruff"
    found = str(candidate) if candidate.exists() else shutil.which("ruff")
    if found is None:
        raise GateUnavailable("ruff is not installed")
    return found


def run_lint_gate() -> Gate:
    """ruff check and ruff format --check must both exit 0."""
    ruff = _ruff()
    checks = {
        "ruff check": [ruff, "check", "."],
        "ruff format --check": [ruff, "format", "--check", "."],
    }
    failed = [
        name
        for name, command in checks.items()
        if _run(command, capture_output=True).returncode != 0
    ]
    return exit_status_gate("lint", "ruff check and ruff format are clean", failed)


def run_tests_gate() -> tuple[Gate, list[TestRecord]]:
    """Run the suite in parallel without race probes and return the gate and every record."""
    with tempfile.TemporaryDirectory() as tmp:
        results = Path(tmp) / "results.json"
        env = {
            **os.environ,
            RESULTS_ENV: str(results),
            "PYTHONPATH": os.pathsep.join(
                [str(Path(__file__).parent), os.environ.get("PYTHONPATH", "")]
            ),
        }
        command = [
            sys.executable,
            "-m",
            "pytest",
            "-p",
            Path(__file__).stem,
            "-n",
            "auto",
            "-m",
            "not race",
            "-q",
        ]
        completed = _run(command, env=env, capture_output=True)
        if not results.exists():
            raise GateUnavailable(
                f"pytest wrote no results (exit code {completed.returncode})"
            )
        records = [
            TestRecord(**{**d, "stories": tuple(d["stories"])})
            for d in json.loads(results.read_text())
        ]
    return judge_tests_gate(records, completed.returncode), records


def run_traceability_gate() -> Gate:
    """scripts/check_story_traceability.py must exit 0."""
    script = REPO_ROOT / "scripts" / "check_story_traceability.py"
    completed = _run([sys.executable, str(script)], capture_output=True)
    return exit_status_gate(
        "traceability",
        "every story has a passing test",
        ["check_story_traceability"] if completed.returncode else [],
    )


def run_leaks_gate() -> Gate:
    """Fetch rooms and messages from RBP and look for leftover qa- data. Fails closed."""
    try:
        bodies = {
            "room": requests.get(
                f"{settings.room_url}/room/", timeout=settings.timeout
            ).text,
            "message": requests.get(
                f"{settings.message_url}/message/", timeout=settings.timeout
            ).text,
        }
    except requests.RequestException as error:
        return Gate("leaks", False, f"RBP not reachable: {type(error).__name__}")
    return leaks_gate(bodies)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic release gate.")
    parser.add_argument(
        "--blocking-issues",
        type=parse_blocking_issues,
        default=frozenset(),
        metavar="2,5",
    )
    parser.add_argument("--json", type=Path, default=None, metavar="PATH")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run every gate, print the table, optionally write JSON and return the exit code."""
    args = parse_args(argv)
    gates: list[Gate] = []
    records: list[TestRecord] = []
    unavailable: list[str] = []
    runners = (
        ("lint", run_lint_gate),
        ("tests", None),
        ("traceability", run_traceability_gate),
        ("leaks", run_leaks_gate),
    )
    for name, runner in runners:
        try:
            if runner is None:
                gate, records = run_tests_gate()
            else:
                gate = runner()
        except GateUnavailable as error:
            unavailable.append(f"{name}: {error}")
            continue
        gates.append(gate)
    known_bugs = collect_known_bugs(records)
    decision = evaluate(gates, known_bugs, args.blocking_issues)
    print("\nRelease gate\n")
    print(format_table(gates, decision))
    for message in unavailable:
        print(f"GATE COULD NOT RUN - {message}")
    if args.json:
        args.json.write_text(
            json.dumps(to_report(gates, known_bugs, decision), indent=2)
        )
    return exit_code(decision.verdict, bool(unavailable))


if __name__ == "__main__":
    sys.exit(main())
