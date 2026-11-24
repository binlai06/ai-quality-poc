"""Unit tests for the release gate decision logic. No RBP and no subprocess needed."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ci"))

from release_gate import (
    Gate,
    KnownBug,
    TestRecord,
    Verdict,
    collect_known_bugs,
    evaluate,
    exit_code,
    judge_tests_gate,
    leaks_gate,
    parse_blocking_issues,
)

pytestmark = [pytest.mark.unit, pytest.mark.regression]

NO_BLOCKING: frozenset[int] = frozenset()


def passing_gates() -> list[Gate]:
    return [Gate("lint", True, "ok"), Gate("tests", True, "ok")]


def test_all_gates_passing_without_known_bugs_is_approved() -> None:
    decision = evaluate(passing_gates(), [], NO_BLOCKING)

    assert decision.verdict is Verdict.APPROVED
    assert decision.reasons


def test_all_gates_passing_with_known_bug_is_approved_with_known_risks() -> None:
    bugs = [KnownBug(4, ("BOOK-1",))]

    decision = evaluate(passing_gates(), bugs, NO_BLOCKING)

    assert decision.verdict is Verdict.APPROVED_WITH_KNOWN_RISKS
    assert decision.reasons == ("known bug #4 (stories: BOOK-1)",)


def test_known_bug_without_issue_number_is_approved_with_known_risks() -> None:
    decision = evaluate(passing_gates(), [KnownBug(None)], NO_BLOCKING)

    assert decision.verdict is Verdict.APPROVED_WITH_KNOWN_RISKS
    assert decision.reasons == ("known bug without issue",)


def test_failed_gate_is_blocked_with_the_gate_reason() -> None:
    gates = [Gate("lint", True, "ok"), Gate("tests", False, "2 failed")]

    decision = evaluate(gates, [], NO_BLOCKING)

    assert decision.verdict is Verdict.BLOCKED
    assert decision.reasons == ("gate tests failed: 2 failed",)


def test_failed_gate_wins_over_known_bugs() -> None:
    gates = [Gate("leaks", False, "RBP not reachable")]

    decision = evaluate(gates, [KnownBug(4)], NO_BLOCKING)

    assert decision.verdict is Verdict.BLOCKED


def test_every_failed_gate_is_listed_in_the_reasons() -> None:
    gates = [
        Gate("lint", False, "a"),
        Gate("tests", True, "ok"),
        Gate("leaks", False, "b"),
    ]

    decision = evaluate(gates, [], NO_BLOCKING)

    assert decision.reasons == ("gate lint failed: a", "gate leaks failed: b")


def test_known_bug_in_blocking_issues_is_blocked() -> None:
    bugs = [KnownBug(2, ("BOOK-2",)), KnownBug(4)]

    decision = evaluate(passing_gates(), bugs, frozenset({2}))

    assert decision.verdict is Verdict.BLOCKED
    assert decision.reasons == ("blocking issue #2",)


def test_blocking_issue_without_matching_known_bug_does_not_block() -> None:
    decision = evaluate(passing_gates(), [KnownBug(4)], frozenset({9}))

    assert decision.verdict is Verdict.APPROVED_WITH_KNOWN_RISKS


def test_blocking_issue_is_reported_once_when_several_entries_share_it() -> None:
    bugs = [KnownBug(2, ("BOOK-1",)), KnownBug(2, ("BOOK-2",))]

    decision = evaluate(passing_gates(), bugs, frozenset({2}))

    assert decision.reasons == ("blocking issue #2",)


def test_failed_gate_and_blocking_issue_report_both_reasons() -> None:
    gates = [Gate("lint", False, "bad format")]

    decision = evaluate(gates, [KnownBug(5)], frozenset({5}))

    assert decision.verdict is Verdict.BLOCKED
    assert decision.reasons == ("gate lint failed: bad format", "blocking issue #5")


def test_no_gates_is_blocked_fail_closed() -> None:
    decision = evaluate([], [], NO_BLOCKING)

    assert decision.verdict is Verdict.BLOCKED
    assert decision.reasons == ("no gates were evaluated",)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("2,5", frozenset({2, 5}), id="two-issues"),
        pytest.param(" 2 , 5 ,", frozenset({2, 5}), id="spaces-and-trailing-comma"),
        pytest.param("7", frozenset({7}), id="one-issue"),
        pytest.param("", frozenset(), id="empty"),
    ],
)
def test_parse_blocking_issues_reads_a_comma_list(
    text: str, expected: frozenset[int]
) -> None:
    assert parse_blocking_issues(text) == expected


@pytest.mark.parametrize(
    "text", [pytest.param("2,x", id="letter"), pytest.param("#2", id="hash")]
)
def test_parse_blocking_issues_with_non_numbers_raises_value_error(text: str) -> None:
    with pytest.raises(ValueError):
        parse_blocking_issues(text)


@pytest.mark.parametrize(
    ("verdict", "unavailable", "expected"),
    [
        pytest.param(Verdict.APPROVED, False, 0, id="approved"),
        pytest.param(
            Verdict.APPROVED_WITH_KNOWN_RISKS, False, 0, id="approved-with-risks"
        ),
        pytest.param(Verdict.BLOCKED, False, 1, id="blocked"),
        pytest.param(Verdict.APPROVED, True, 2, id="gate-could-not-run"),
        pytest.param(Verdict.BLOCKED, True, 2, id="blocked-and-gate-could-not-run"),
    ],
)
def test_exit_code_maps_verdict_and_gate_availability(
    verdict: Verdict, unavailable: bool, expected: int
) -> None:
    assert exit_code(verdict, unavailable) == expected


def record(outcome: str, reason: str = "", *stories: str) -> TestRecord:
    return TestRecord(
        nodeid="tests/x.py::t", outcome=outcome, reason=reason, stories=stories
    )


def test_xfailed_tests_become_one_known_bug_per_issue_with_sorted_stories() -> None:
    records = [
        record("xfailed", "RBP bug #4: unknown room returns 500", "BOOK-2"),
        record("xfailed", "RBP bug #4: unknown room returns 500", "BOOK-1"),
        record("xfailed", "RBP bug #2: something else"),
    ]

    bugs = collect_known_bugs(records)

    assert bugs == [KnownBug(2, ()), KnownBug(4, ("BOOK-1", "BOOK-2"))]


def test_xfail_reason_without_issue_number_becomes_known_bug_without_issue() -> None:
    bugs = collect_known_bugs([record("xfailed", "flaky", "BOOK-1")])

    assert bugs == [KnownBug(None, ("BOOK-1",))]


def test_passed_and_failed_tests_are_not_known_bugs() -> None:
    records = [record("passed", "RBP bug #4: x"), record("failed", "RBP bug #5: y")]

    assert collect_known_bugs(records) == []


@pytest.mark.parametrize("outcome", ["failed", "error", "xpass_strict"])
def test_tests_gate_fails_on_failed_error_or_strict_xpass(outcome: str) -> None:
    gate = judge_tests_gate([record("passed"), record(outcome)], returncode=1)

    assert not gate.passed
    assert outcome.replace("_", " ") in gate.reason


def test_tests_gate_fails_when_pytest_exit_code_is_not_zero_without_bad_records() -> (
    None
):
    gate = judge_tests_gate([record("passed")], returncode=2)

    assert not gate.passed
    assert "code 2" in gate.reason


def test_tests_gate_passes_with_passed_xfailed_and_non_strict_xpass() -> None:
    records = [record("passed"), record("xfailed", "RBP bug #4: x"), record("xpassed")]

    gate = judge_tests_gate(records, returncode=0)

    assert gate.passed
    assert gate.reason == "1 passed, 1 xfailed"


def test_leaks_gate_passes_when_no_qa_data_is_left() -> None:
    bodies = {
        "room": '{"rooms":[{"roomName":"101"}]}',
        "message": '[{"subject":"Hello"}]',
    }

    assert leaks_gate(bodies).passed


@pytest.mark.parametrize(
    ("bodies", "expected"),
    [
        pytest.param(
            {"room": '{"roomName":"qa-room-ab12"}', "message": "[]"},
            "1 leaked rooms",
            id="room",
        ),
        pytest.param(
            {"room": "[]", "message": "qa-subject-x1 qa-subject-x2"},
            "2 leaked message subjects",
            id="subject",
        ),
        pytest.param(
            {"room": "[]", "message": "qa0123abcd Guestdeadbeef"},
            "1 leaked message guests",
            id="guest",
        ),
    ],
)
def test_leaks_gate_fails_when_qa_data_is_left(
    bodies: dict[str, str], expected: str
) -> None:
    gate = leaks_gate(bodies)

    assert not gate.passed
    assert gate.reason == expected
