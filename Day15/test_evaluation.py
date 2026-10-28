"""Evaluate Day15 references against Day14 functions without a live MCP server.

Run from the project root: python -m pytest Day15/test_evaluation.py -v
"""

import copy
import json
from pathlib import Path

import pytest

from Day14 import mcp_server as server


DATASET_PATH = Path(__file__).with_name("golden_dataset.jsonl")
CASES = [json.loads(line) for line in DATASET_PATH.read_text(encoding="utf-8").splitlines()
         if line.strip()]
TOOLS = {
    "get_available_leave_balance": server.get_available_leave_balance,
    "create_leave_request": server.create_leave_request,
}


def assert_json_subset(expected, actual, path="result"):
    """Check reference fields while permitting extra response metadata."""
    assert type(actual) is type(expected), f"{path}: expected {type(expected).__name__}, got {type(actual).__name__}"
    if isinstance(expected, dict):
        for key, value in expected.items():
            assert key in actual, f"{path}: missing {key}"
            assert_json_subset(value, actual[key], f"{path}.{key}")
    else:
        assert actual == expected, f"{path}: expected {expected!r}, got {actual!r}"


def test_dataset_contract():
    """Fail malformed references before treating gaps as expected failures."""
    assert CASES, "Dataset is empty"
    identifiers = [case["id"] for case in CASES]
    assert len(identifiers) == len(set(identifiers)), "Duplicate case IDs"
    required = {
        "id", "category", "input", "expected_output", "initial_balances",
        "expected_tool_calls", "expected_final_balances", "expected_request_count",
        "known_gap", "gap_note",
    }
    for case in CASES:
        assert set(case) == required, case["id"]
        for key in ("id", "category", "input", "expected_output"):
            assert isinstance(case[key], str) and case[key].strip(), (case["id"], key)
        assert type(case["known_gap"]) is bool
        assert isinstance(case["gap_note"], str)
        assert bool(case["gap_note"].strip()) == case["known_gap"]
        for key in ("initial_balances", "expected_final_balances"):
            assert set(case[key]) == set(server.LEAVE_DATA)
            assert all(type(value) is int and value >= 0 for value in case[key].values())
        assert type(case["expected_request_count"]) is int and case["expected_request_count"] >= 0
        assert isinstance(case["expected_tool_calls"], list) and case["expected_tool_calls"]
        for call in case["expected_tool_calls"]:
            assert set(call) == {"tool", "arguments", "expected_result"}
            assert call["tool"] in TOOLS
            arguments = {"user_id"} if call["tool"] == "get_available_leave_balance" else {"user_id", "date", "reason"}
            assert set(call["arguments"]) == arguments
            assert all(isinstance(value, str) for value in call["arguments"].values())
            assert isinstance(call["expected_result"], dict) and call["expected_result"]


@pytest.fixture
def isolated_state():
    """Only mutate this test process; preserve state for other tests importing it."""
    employees = copy.deepcopy(server.LEAVE_DATA)
    cache = copy.deepcopy(server.IDEMPOTENCY_CACHE)
    server.IDEMPOTENCY_CACHE.clear()
    try:
        yield
    finally:
        server.LEAVE_DATA.clear()
        server.LEAVE_DATA.update(employees)
        server.IDEMPOTENCY_CACHE.clear()
        server.IDEMPOTENCY_CACHE.update(cache)


def case_parameter(case):
    marks = []
    if case["known_gap"]:
        marks.append(pytest.mark.xfail(reason=case["gap_note"], strict=True, raises=AssertionError))
    return pytest.param(case, id=f"{case['id']}-{case['category']}", marks=marks)


@pytest.mark.parametrize("case", [case_parameter(case) for case in CASES])
def test_reference_scenario(case, isolated_state):
    for user_id, balance in case["initial_balances"].items():
        server.LEAVE_DATA[user_id]["leave_balance"] = balance

    # Collect mismatches so final state is checked even if a tool response differs.
    mismatches = []
    for index, call in enumerate(case["expected_tool_calls"], 1):
        actual = json.loads(TOOLS[call["tool"]](**call["arguments"]))
        try:
            assert_json_subset(call["expected_result"], actual, f"call[{index}]")
        except AssertionError as error:
            mismatches.append(str(error))

    balances = {user: data["leave_balance"] for user, data in server.LEAVE_DATA.items()}
    if balances != case["expected_final_balances"]:
        mismatches.append(f"Final balances: expected {case['expected_final_balances']}, got {balances}")
    count = len(server.IDEMPOTENCY_CACHE)
    if count != case["expected_request_count"]:
        mismatches.append(f"Cached requests: expected {case['expected_request_count']}, got {count}")
    assert not mismatches, "\n".join(mismatches)
