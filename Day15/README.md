# Day 15: Golden Dataset and Evaluation Plan

This assignment defines repeatable evaluation cases for the HR leave assistant
and its Day14 MCP tools. It extends Day13's response-phrase checks with explicit
tool arguments, expected JSON results, and final state checks. It also provides
a reference for human review and a future LLM judge.

The dataset contains **30 synthetic cases**: 24 regression cases based on the
current Day14 behavior and 6 target-policy cases that expose known validation
and idempotency limitations. No employee data in this folder represents real
people or real leave requests.

## Files and current status

| File | Purpose | Status |
| --- | --- | --- |
| `golden_dataset.jsonl` | One evaluation case per line, including ordered tool calls and expected state. | Populated with 30 cases. |
| `README.md` | Dataset contract, evaluation workflow, scoring, and limitations. | This guide. |
| `rubric.md` | Future standalone rubric for the judge and human reviewers. | Empty placeholder. |
| `judge.py` | Future evaluator that compares an assistant's answer and trace with the reference. | Empty placeholder. |
| `human_labels.csv` | Future human ratings and adjudication notes. | Empty placeholder. |
| `test_evaluation.py` | Pytest runner validating dataset structure, reference tool results, final balances, and cached request counts. | Implemented; isolates state for each case. |

The deterministic pytest runner is implemented. The LLM judge and human review
files remain empty placeholders; running `judge.py` does not evaluate answers.
Day13's harness does not load this JSONL file automatically.

Run the checks from the project root using the project's virtual environment:

```powershell
.\venv\Scripts\python.exe -m pytest Day15/test_evaluation.py -v -p no:cacheprovider
```

The current baseline is **25 passed, 6 xfailed**: one dataset-contract check,
24 passing regression cases, and six expected failures for known Day14 gaps.
`XFAIL` means the desired behavior is still missing; it is not a passing policy
check. The known-gap cases use strict expected-failure markers, so an unexpected
pass prompts a review of the marker and reference. To see those failures as
ordinary failing tests, add `--runxfail --tb=short` to the command.

The runner calls Day14 functions in its own process and checks state directly.
It does not require a running MCP server, change a VS Code server's balances,
or evaluate model responses, MCP transport, and human/LLM judge agreement.
For a machine-readable test report, add `--junitxml=Day15/evaluation_results.xml`.

## What is being evaluated

The assistant should select the appropriate tool, supply the required arguments,
report the result accurately, and respect the tool's outcome. Correct wording
alone is insufficient: a successful leave request must have a corresponding
write call and the expected balance deduction.

Day14 offers these tools:

| Tool | Required arguments | Current behavior |
| --- | --- | --- |
| `get_available_leave_balance` | `user_id` | Returns employee details and balance, or `USER_NOT_FOUND`. |
| `create_leave_request` | `user_id`, `date`, `reason` | Creates one day of leave when balance is available. Caches successful requests using uppercased employee ID and the exact date string. |

The fixture starts with E101/Priya at 3 days, E102/Rahul at 0 days, and
E103/Anita at 5 days. Employee IDs are matched case-insensitively. Successful
requests and balances are stored in memory and reset when the server restarts.

## JSONL format

Read the file as UTF-8 and parse each nonempty line as an independent JSON object.
There is no enclosing JSON array. Each record has these fields:

| Field | Meaning |
| --- | --- |
| `id` | Stable unique identifier, `D15-001` through `D15-030`. |
| `category` | Coverage group such as `lookup`, `balance_guard`, or `validation_gap`. |
| `input` | User request or ordered scenario to present to the assistant. |
| `expected_output` | Semantic reference answer for human or LLM review; exact wording is optional. |
| `initial_balances` | Starting balance for every fixture employee. |
| `expected_tool_calls` | Ordered reference operations. Each contains `tool`, `arguments`, and `expected_result`. |
| `expected_final_balances` | Expected balance for every fixture employee after the entire case. |
| `expected_request_count` | Number of unique successful requests in the idempotency cache after the case. |
| `known_gap` | Whether this case specifies target behavior missing from the current Day14 server. |
| `gap_note` | Explanation of the missing behavior; empty for regression cases. |

`expected_result` is a recursive JSON subset. Parse the JSON string returned by
Day14 before comparing it. For example, `{"status": "SUCCESS", "leave_balance": 3}`
matches a response with additional `name` and `user_id` fields. Compare types as
well as values. Ignore JSON key order and natural-language message wording.

For tool-level regression, execute the reference calls in order. For end-to-end
assistant evaluation, provide `input` and capture actual tool calls and responses;
keep the reference answer hidden from the assistant. Extra read-only balance
checks are acceptable. Require the reference write attempts in order, including
intentional duplicate attempts, and reject additional writes.

## Coverage

- Balance lookup: all fixture employees, zero balance, lowercase IDs, unknown IDs,
  empty IDs, and repeated reads that leave state unchanged.
- Leave creation: different employees, lowercase IDs, different dates, and
  independent requests for different employees on the same date.
- Balance enforcement: no balance, repeated rejected writes, exhausting a balance,
  and refusing a subsequent request without making the balance negative.
- Idempotency: exact duplicates, case-insensitive IDs, duplicates after balance
  exhaustion, and replaying an earlier response after a later successful write.
- Target policies: malformed dates, impossible calendar dates, empty or whitespace
  reasons, changed payloads for an existing key, and noncanonical date strings.

The dates in the fixture are fixed examples, not festival dates. Current Day14
does not implement a past-date policy, festival lookup, multi-day leave, persistent
storage, authorization, or concurrent request guarantees. These cases do not
establish those capabilities.

## Running an evaluation

1. Install the root requirements and confirm Day14 starts as described in the
   [root README](../README.md).
2. Load a case and start a fresh Day14 server process for it. In a future in-process
   runner, explicitly restore all initial balances and clear `IDEMPOTENCY_CACHE`.
   Preserve state between the ordered operations inside the case.
3. Execute the tool-level reference sequence, or submit the input to an assistant
   connected to the fresh server. Record raw calls, results, latency, and errors.
4. Compare returned JSON subsets, final balances, and successful request count.
   A backend runner can inspect state directly. An MCP-only client can verify
   balances using read calls; it should mark cache-count verification unavailable
   unless it has a separate inspection mechanism.
5. Review the final answer against `expected_output`. Confirm that reported
   employee IDs, dates, approvals, rejections, and balances agree with the trace.
6. Store observations and scores in a separate results file. Keep the golden
   references unchanged, and report known-gap cases separately.

Do not run all records against one continuously running server: balances from
one case would contaminate later cases. A repeated response may include the
balance at the time of the original request; use a fresh lookup or final state
inspection for the current balance.

## Suggested scoring and human review

Use deterministic checks for tool names, arguments, error codes, JSON subsets,
and state. Use a human or LLM judge only for answer quality, clarity, and whether
the explanation follows the observed result. An LLM verdict cannot prove a
balance changed or a tool executed.

| Dimension | Pass condition |
| --- | --- |
| Tool use | Required operations use the correct tool and arguments, with no extra writes. |
| Result accuracy | Expected JSON fields match the observed tool results. |
| State integrity | Final balances and unique request count match the reference. |
| Answer quality | Final answer communicates the result without invented approvals or deductions. |

A case passes only when all applicable checks pass. Record unavailable checks
as `NOT_VERIFIED`; do not silently count them as passes. Report regression
pass rate as passed regression cases divided by 24, and target-policy pass rate
as passed known-gap cases divided by 6. Also report exceptions and unverified
cases, rather than removing them from the denominator.

Suggested future human-label columns are `case_id`, `reviewer_id`,
`tool_use_pass`, `result_pass`, `state_pass`, `answer_pass`, `overall_label`,
and `notes`. Use `PASS`, `FAIL`, or `NOT_VERIFIED` where appropriate. Review
disagreements against the actual trace before changing a reference label.

## Known implementation gaps

The six `known_gap: true` records are specifications for desired behavior,
not claims that Day14 implements it today:

- Invalid or noncanonical dates should return `INVALID_DATE` without mutation.
  Day14 currently accepts any string as a date.
- Blank reasons should return `INVALID_REASON` without mutation. Day14 currently
  accepts empty and whitespace-only strings.
- Reusing an employee/date key with a changed reason should return
  `IDEMPOTENCY_CONFLICT` and preserve the original request. Day14 currently
  replays the original request without comparing the reason.

Keep these cases visible when reporting results. They distinguish current
regression coverage from work still needed to meet the target policies.

## Maintaining the dataset

Keep IDs stable. Add new IDs for new scenarios, use synthetic data, and describe
the policy before adding its expected result. Update the case counts and report
denominators if coverage changes. Review reference results against the server
implementation and record intentional behavior changes before updating labels.
