# AI Engineering Project

Assignment code for the AI Engineering course, organized one folder per day.
Each folder holds that day's code and its reflection PDF.

## Structure

| Folder | What it contains |
| --- | --- |
| [Day01/](Day01/) | `chatbot.py` and `main.py`: a multi-turn chatbot that talks to a local Ollama model and keeps conversation history. |
| [Day02/](Day02/) | `experiment.py`: runs the same question through three prompt versions against an OpenAI-compatible endpoint to compare results. |
| [Day03/](Day03/) | `reliability_test.py`: an interactive suite that checks how the LLM handles valid, malformed, incomplete and mistyped JSON, plus timeouts. |
| [Day04/](Day04/) | A FastAPI service with SQLite storage for tasks and customers. Includes CRUD routes, validation and pytest tests. |
| [Day05-08/](Day05-08/) | Document pipeline and grounded RAG: Markdown parsing, chunking, embedding retrieval, and an Ollama-based answer generator with citations and evaluation scripts. |
| [Day09/](Day09/) | Engineering reflection PDF on architecture strategy. No code. |
| [Day10/](Day10/) | `main.py`: an enterprise HR assistant on Ollama with a read-only leave-balance tool and a write tool for leave requests. Pydantic validates tool arguments, and write actions need human confirmation (or `AUTO_CONFIRM_WRITES=true`). Writes `day10_execution.log`. Also includes the reflection PDF. |
| [Day11/](Day11/) | `main.py`: a ReAct-style agent for leave requests that reasons, calls tools, and reports a final answer using Ollama. |
| [Day12/](Day12/) | `main.py`: a local leave-request demo with idempotency keys, deterministic balance enforcement, and Pydantic validation. Verifies duplicate replay, conflicting key reuse, insufficient balance, and invalid inputs. Appends events to `day12_audit_trail.log` in the project root. |
| [Day13/](Day13/) | `test_harness.py`: a golden regression harness for the Day12 agent, with five cases covering valid leave requests, duplicate submissions, insufficient balance, balance lookup, and unknown festivals. Checks response phrases and reports pass rate and latency in `Day13/golden_test_results.json`. Also includes the engineering reflection PDF. Requires the Day12 agent components described below. |
| [Day14/](Day14/) | `mcp_server.py`: a FastMCP server exposing leave-balance lookup and one-day leave creation over MCP stdio. Enforces available balance and replays duplicate requests by employee ID and date. Includes a VS Code connection in `.vscode/mcp.json`. |
| [Day15/](Day15/) | `golden_dataset.jsonl`: 30 synthetic HR leave evaluation cases. `test_evaluation.py` checks dataset structure, Day14 tool results, final balances, and cached request counts with isolated state per case. Current baseline: 25 passed and 6 expected failures. `judge.py` is an Ollama-based LLM judge that writes `baseline_results.jsonl`; its output is not yet validated. Rubric and human review files are empty. |
| [Day16/](Day16/) | AI observability demos: `instrumentation.py` records local traces with email and employee-ID masking and simulated retrieval/tool faults. `judge.py` uses Ollama to score simulated responses to the Day15 dataset, saving results and per-case traces. `check_langsmith.py` provides a LangSmith tracing smoke check. |

Each day's folder has its own `CLAUDE.md` or `readme.md` where one exists, with
details for that assignment.

## Setup

Requirements: Python 3.10 or newer. Some scripts also need a local
[Ollama](https://ollama.com) service with `llama3` pulled.

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the project root for the scripts that call an
OpenAI-compatible endpoint (Day 02, Day 03):

```text
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
```

Optional: `OLLAMA_MODEL` selects the Ollama model (defaults to `llama3`).
Do not commit `.env`; it is listed in `.gitignore`.

## Running

Run commands from the project root:

```powershell
python Day01/main.py                                  # chatbot
python Day02/experiment.py                            # prompt comparison
python Day03/reliability_test.py                      # reliability suite
python Day10/main.py                                  # HR assistant (runs a sample leave request)
python -m uvicorn Day04.main:app --reload             # API at http://127.0.0.1:8000/docs
python Day11/main.py                                  # leave-request agent
python Day12/main.py                                  # leave-request validation and audit trail demo
python -m Day13.test_harness                          # golden regression suite (requires Day12 agent components below)
python Day14/mcp_server.py                            # MCP stdio server (waits for an MCP client)
python Day16/instrumentation.py                       # local tracing and PII-masking demo
python Day16/check_langsmith.py                       # LangSmith tracing smoke check
python Day16/judge.py                                 # Ollama judge with local per-case traces
```

Day12 runs without Ollama or an API key. It prints `PASS` messages for its checks
and the location of `day12_audit_trail.log`. Balances and idempotency keys are
stored in memory and reset each run; the audit log keeps entries from previous
runs, grouped by a unique run ID.

Day13 expects `run_reliable_agent`, `APPROVED_REQUESTS`, and `IDEMPOTENCY_CACHE`
from `Day12/main.py`. The current Day12 local demo does not define these, so
Day13 will fail at import until a compatible agent implementation is available.
Run the harness as a module from the project root so its `Day12` import resolves.
Once that dependency is satisfied, it runs the five cases in order, prints an
evaluation summary, and writes `Day13/golden_test_results.json`. Its checks match
phrases in agent responses; they do not directly verify backend state or schemas.

Day14 exposes two tools through the Model Context Protocol (MCP):

| Tool | Arguments | Behavior |
| --- | --- | --- |
| `get_available_leave_balance` | `user_id` | Returns the employee's name and leave balance, or `USER_NOT_FOUND`. |
| `create_leave_request` | `user_id`, `date`, `reason` | Deducts one day if available; rejects insufficient balance and replays an existing request for the same employee and date without another deduction. |

Install dependencies using the setup command above; `requirements.txt` includes
FastMCP. The server itself needs no Ollama service or API key. Running it directly
starts a stdio server that waits for MCP messages rather than opening a web page
or an interactive prompt. Press Ctrl+C to stop a manually started instance.

To test Day14 through GitHub Copilot in VS Code:

1. Open this project root in VS Code. The workspace configuration is
   [.vscode/mcp.json](.vscode/mcp.json), using `venv/Scripts/python.exe` to launch
   `Day14/mcp_server.py` as `enterprise-hr-leave`.
2. Open GitHub Copilot Chat inside VS Code, select Agent mode, and send a message
   to initialize the chat session. If startup reports that the session runtime
   has not been created, send a message before retrying Start.
3. Open `.vscode/mcp.json` and click Start above `enterprise-hr-leave`. Let VS Code
   launch the server; a separate terminal instance is unnecessary. Enable its
   tools in Chat if needed, and approve tool calls when prompted.
4. Ask Copilot to use the server for the following checks, in order. Expand the
   tool calls to inspect the actual arguments and returned JSON.

| Check | Request to make through Copilot | Expected result on a fresh server |
| --- | --- | --- |
| Balance lookup | Check E101's leave balance. | 3 days. |
| Create leave | Create leave for E101 on 2026-11-10, reason: Personal trip. | Success; 2 days remain. |
| Duplicate request | Call `create_leave_request` again with the same arguments. | `idempotent_replay: true`; balance stays at 2. |
| Verify balance | Check E101's leave balance again. | 2 days. |
| Balance guard | Create leave for E102 on 2026-11-10, reason: Personal trip. | `INSUFFICIENT_BALANCE`. |
| Unknown employee | Check E999's leave balance. | `USER_NOT_FOUND`. |

The flow is: Copilot prompt -> MCP tool call -> Python function -> JSON result
-> Copilot response. Day14 uses its own in-memory demo data; balances and the
duplicate-request cache reset whenever the server restarts. It does not write
Day12's audit log.

Tests:

```powershell
python -m pytest Day04/test_main.py
python -m unittest discover -s Day05-08 -p "test_*.py" -v
python -m pytest Day15/test_evaluation.py -v -p no:cacheprovider
```

Day15 evaluates Day14 functions directly, so it needs neither a running MCP
server nor an LLM connection. Its baseline is **25 passed, 6 xfailed**: one
dataset-contract check, 24 regression cases, and six known gaps covering invalid
dates, blank reasons, and conflicting reasons on duplicate requests. `XFAIL`
records missing target behavior; it does not mean that behavior passed.

Add `--runxfail --tb=short` to report the six gaps as ordinary failures, or
`--junitxml=Day15/evaluation_results.xml` to save an XML report. The current
runner checks backend behavior; MCP transport, model answers, LLM judging, and
human review are not evaluated. `judge.py` runs an Ollama LLM judge over the
dataset and writes `Day15/baseline_results.jsonl`; its verdicts are not yet
validated against human labels. `rubric.md` and `human_labels.csv` remain empty
placeholders. See [Day15/README.md](Day15/README.md) for the dataset
format, evaluation workflow, and scoring guidance.

Day16's instrumentation demo runs without Ollama or LangSmith and writes
`Day16/traces/D15-03_trace.json`. It records simulated retrieval, LLM, and tool
steps, masking email addresses and employee IDs matching `E` plus three or four
digits in the input. Its `trace_request` function accepts `slow_tool` (a
three-second delay), `flaky_tool`, `mcp_error`, and `bad_retrieval` fault flags
for debugging; the standalone command runs without a fault flag.

The LangSmith smoke check loads the root `.env`, calls a function decorated with
`traceable`, and prints `result: 5`. Configure LangSmith tracing and credentials
in your environment to send that trace to LangSmith. The other Day16 scripts
write local JSON files and do not send traces to LangSmith.

Day16's judge requires a running Ollama service with `llama3` available, or the
model selected by `OLLAMA_MODEL`. It reads `Day15/golden_dataset.jsonl` and
overwrites `Day16/evaluation_results.jsonl` and matching
`Day16/traces/<case_id>_judge_trace.json` files. These contain masked inputs,
verdicts, reasons, model metadata (in traces), and latency. The assistant responses
are simulated; the script does not execute the HR agent or its tools. It reads
an optional `expected` field and otherwise uses a generic expected-behavior
fallback. Parsing failures or execution errors can default to Level 3 (Pass),
so these verdicts should not be treated as validated agent-quality scores.

RAG and chunking commands for Day 05-08 are in
[Day05-08/readme.md](Day05-08/readme.md).
