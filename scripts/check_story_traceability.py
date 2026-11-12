"""Story traceability check: does every user story have at least one passing test?

Deterministic: no LLM, no network. The script runs pytest in a subprocess, with
a small plugin (this same file) that records each test's outcome and its
story("<id>") markers. The verdict comes from a pure function, `evaluate`.

Usage: python scripts/check_story_traceability.py
Exit code 0 only when every story is covered and no story marker is unknown.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STORIES_FILE = REPO_ROOT / "docs" / "stories.md"
RESULTS_ENV = "STORY_TRACEABILITY_RESULTS"
OUTCOMES = ("passed", "xfailed", "failed", "skipped", "deselected")


@dataclass(frozen=True)
class TestResult:
    """Outcome of one test and the story ids from its markers."""

    __test__ = False  # not a pytest test class

    stories: tuple[str, ...]
    outcome: str


@dataclass(frozen=True)
class StoryReport:
    """Counts and verdict for one story."""

    story: str
    tests: int
    passed: int
    xfailed: int
    failed: int
    covered: bool

    @property
    def verdict(self) -> str:
        return "COVERED" if self.covered else "NOT COVERED"


@dataclass(frozen=True)
class Evaluation:
    """Result of the whole check."""

    reports: list[StoryReport]
    unknown: list[str]

    @property
    def ok(self) -> bool:
        return all(r.covered for r in self.reports) and not self.unknown


def evaluate(stories: list[str], results: list[TestResult]) -> Evaluation:
    """Pure decision logic. A story is covered when it has at least one passed test."""
    reports = [_report_for(story, results) for story in stories]
    seen = {story for result in results for story in result.stories}
    unknown = sorted(seen - set(stories))
    return Evaluation(reports=reports, unknown=unknown)


def _report_for(story: str, results: list[TestResult]) -> StoryReport:
    outcomes = [r.outcome for r in results if story in r.stories]
    passed = outcomes.count("passed")
    return StoryReport(
        story=story,
        tests=len(outcomes),
        passed=passed,
        xfailed=outcomes.count("xfailed"),
        failed=outcomes.count("failed"),
        covered=passed > 0,
    )


def parse_stories(markdown: str) -> list[str]:
    """Read story ids from the first column of the markdown table."""
    ids = []
    for line in markdown.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if re.fullmatch(r"[A-Z]+-\d+", cells[0]):
            ids.append(cells[0])
    return ids


def format_table(evaluation: Evaluation) -> str:
    """Render the evaluation as a plain text table."""
    header = ("story", "tests", "passed", "xfailed", "failed", "verdict")
    rows = [
        (r.story, r.tests, r.passed, r.xfailed, r.failed, r.verdict)
        for r in evaluation.reports
    ]
    rows += [(story, "-", "-", "-", "-", "UNKNOWN") for story in evaluation.unknown]
    table = [header] + [tuple(str(c) for c in row) for row in rows]
    widths = [max(len(row[i]) for row in table) for i in range(len(header))]
    return "\n".join(
        "  ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()
        for row in table
    )


class _RecorderPlugin:
    """Pytest plugin, loaded in the subprocess. Writes outcomes and markers to a JSON file."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.stories: dict[str, tuple[str, ...]] = {}
        self.outcomes: dict[str, str] = {}

    @staticmethod
    def _story_ids(item) -> tuple[str, ...]:
        return tuple(str(m.args[0]) for m in item.iter_markers("story") if m.args)

    def pytest_collection_modifyitems(self, items) -> None:
        for item in items:
            self.stories[item.nodeid] = self._story_ids(item)

    def pytest_deselected(self, items) -> None:
        for item in items:
            self.stories[item.nodeid] = self._story_ids(item)
            self.outcomes[item.nodeid] = "deselected"

    def pytest_runtest_logreport(self, report) -> None:
        outcome = self._outcome(report)
        if outcome:
            self.outcomes[report.nodeid] = outcome

    @staticmethod
    def _outcome(report) -> str | None:
        """Map one report to an outcome, or None if it changes nothing."""
        wasxfail = hasattr(report, "wasxfail")
        if report.failed:
            return "failed"
        if report.when == "call":
            if report.skipped:
                return "xfailed" if wasxfail else "skipped"
            return "failed" if wasxfail else "passed"
        if report.skipped:
            return "xfailed" if wasxfail else "skipped"
        return None

    def pytest_sessionfinish(self) -> None:
        data = [
            {
                "stories": self.stories[nodeid],
                "outcome": self.outcomes.get(nodeid, "skipped"),
            }
            for nodeid in self.stories
        ]
        Path(self.path).write_text(json.dumps(data))


def pytest_configure(config) -> None:
    """Register the recorder when the results file is requested (subprocess only)."""
    path = os.environ.get(RESULTS_ENV)
    if path:
        config.pluginmanager.register(_RecorderPlugin(path))


def run_pytest() -> list[TestResult]:
    """Run the normal suite in a subprocess and return the recorded results."""
    with tempfile.TemporaryDirectory() as tmp:
        results_path = str(Path(tmp) / "results.json")
        env = {
            **os.environ,
            RESULTS_ENV: results_path,
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
            "-m",
            "not race",
            "-q",
        ]
        subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
        data = json.loads(Path(results_path).read_text())
    return [TestResult(tuple(d["stories"]), d["outcome"]) for d in data]


def main() -> int:
    """Run the suite, print the story table and return the exit code."""
    stories = parse_stories(STORIES_FILE.read_text())
    evaluation = evaluate(stories, run_pytest())
    print("\nStory traceability\n")
    print(format_table(evaluation))
    return 0 if evaluation.ok else 1


if __name__ == "__main__":
    sys.exit(main())
