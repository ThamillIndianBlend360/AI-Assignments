# Day 05: Document Parsing and Chunking

Keep all assignment code, examples, and outputs in `Day05-08/`. Use Python's
standard library and local files. Do not modify the Day 04 API or import earlier
assignments. The original Day 05 parsing/chunking code uses no embeddings,
vector search, or LLM calls. The user has authorized continuation in this folder:
Day 06 retrieval lives in `retriever.py`; Day 07 RAG lives in `rag.py` and reuses
that retriever with local Ollama generation. No agents or MCP in the application.

`sample_doc.md` is the single content source for retrieval and RAG. Do not
duplicate policies in Python. Preserve source metadata and document fingerprints.
`rag.py` renders model-selected source sentences with actual chunk citations;
do not restore unrestricted claims that can contradict their cited passages.

Day 08 evaluates this same pipeline using `day08_cases.json` and
`evaluate_rag.py`. Freeze the source document and dataset across baseline and
candidate runs. Change one response policy only, retain failed cases, and inspect
individual answers. No LLM judge as the primary evaluator. Preserve baseline
reports and compare controls before attributing improvements.

- `parser.py` normalizes Markdown and retains blocks, heading paths, and offsets.
- `chunkers.py` builds character windows and whole heading sections.
- `metadata.py` attaches zero-based chunk IDs, source, strategy, and section context.
- `compare_chunks.py` evaluates six quality dimensions and prints evidence.
- `sample_doc.md` is a fictional internal handbook for reproducible evaluation.

Fixed-size defaults are 400 characters with 50 characters of overlap. Offsets
refer to normalized text, not source-file bytes. Structural chunks have no size
cap, preserving complete rules and tables; report the tradeoff of long sections.
Windows crossing headings must retain every intersecting heading path. Preserve
list item order, table row/column relationships, and code identifiers.

The parser supports the Markdown subset documented in its module docstring;
full CommonMark, embedded HTML, PDFs, and Word documents are outside this scope.

From the project root:

```powershell
python Day05-08/compare_chunks.py
python -m unittest discover -s Day05-08 -p "test_*.py" -v
```

The comparison accepts `--document`, `--chunk-size`, `--overlap`, and optional
`--output` for a JSON artifact inside `Day05-08/`. The six semantic probes target
the sample handbook; absent probes in another document are marked SKIP. A WARN
is a measured strategy tradeoff, not an execution error. Integrity failures exit
nonzero. No network access or additional dependency installation is required.
