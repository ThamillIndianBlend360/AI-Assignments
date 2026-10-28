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

Tests:

```powershell
python -m pytest Day04/test_main.py
python -m unittest discover -s Day05-08 -p "test_*.py" -v
```

RAG and chunking commands for Day 05-08 are in
[Day05-08/readme.md](Day05-08/readme.md).
