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
| [Day11/](Day11/) | `main.py`: a ReAct-style agent for leave requests that reasons, calls tools, and reports a final answer using Ollama. |

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
python -m uvicorn Day04.main:app --reload             # API at http://127.0.0.1:8000/docs
python Day11/main.py                                  # leave-request agent
```

Tests:

```powershell
python -m pytest Day04/test_main.py
python -m unittest discover -s Day05-08 -p "test_*.py" -v
```

RAG and chunking commands for Day 05-08 are in
[Day05-08/readme.md](Day05-08/readme.md).
