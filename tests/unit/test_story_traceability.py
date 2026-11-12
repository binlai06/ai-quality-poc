"""Unit tests for the story traceability decision logic. No RBP needed."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from check_story_traceability import TestResult, evaluate

pytestmark = [pytest.mark.unit, pytest.mark.regression]


def result(outcome: str, *stories: str) -> TestResult:
    return TestResult(stories=stories, outcome=outcome)


def test_all_stories_with_a_passed_test_pass_the_check() -> None:
    results = [result("passed", "BOOK-1"), result("passed", "BOOK-2")]

    evaluation = evaluate(["BOOK-1", "BOOK-2"], results)

    assert evaluation.ok
    assert [r.verdict for r in evaluation.reports] == ["COVERED", "COVERED"]


def test_story_with_no_tests_fails_the_check() -> None:
    evaluation = evaluate(["BOOK-1", "BOOK-2"], [result("passed", "BOOK-1")])

    assert not evaluation.ok
    assert evaluation.reports[1].tests == 0
    assert evaluation.reports[1].verdict == "NOT COVERED"


def test_story_with_only_xfailed_tests_fails_the_check() -> None:
    results = [result("xfailed", "BOOK-1"), result("xfailed", "BOOK-1")]

    evaluation = evaluate(["BOOK-1"], results)

    assert not evaluation.ok
    assert evaluation.reports[0].xfailed == 2
    assert evaluation.reports[0].passed == 0


def test_story_with_one_passed_among_xfailed_and_failed_passes_the_check() -> None:
    results = [
        result("xfailed", "BOOK-1"),
        result("failed", "BOOK-1"),
        result("passed", "BOOK-1"),
    ]

    evaluation = evaluate(["BOOK-1"], results)

    assert evaluation.ok
    counts = evaluation.reports[0]
    assert (counts.tests, counts.passed, counts.xfailed, counts.failed) == (3, 1, 1, 1)


def test_unknown_story_marker_fails_the_check() -> None:
    results = [result("passed", "BOOK-1"), result("passed", "BOOK-99")]

    evaluation = evaluate(["BOOK-1"], results)

    assert not evaluation.ok
    assert evaluation.unknown == ["BOOK-99"]


@pytest.mark.parametrize("outcome", ["skipped", "deselected", "failed"])
def test_story_with_only_non_passing_outcome_fails_the_check(outcome: str) -> None:
    evaluation = evaluate(["BOOK-1"], [result(outcome, "BOOK-1")])

    assert not evaluation.ok
    assert evaluation.reports[0].passed == 0
