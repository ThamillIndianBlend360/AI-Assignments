# Day 05-08: Document Preparation & Grounded RAG

`sample_doc.md` is the single source of policy content. Edit it to change the
knowledge available to RAG. It is a fictional training handbook.

```text
sample_doc.md -> parser -> structural chunks -> embeddings -> retrieval -> rag.py
```

The vector index is stored in memory and rebuilt when the Markdown changes.
There is no separate hardcoded policy list or persistent vector database.

## Files

| File | Purpose |
| --- | --- |
| `sample_doc.md` | Source policies: leave, travel, expenses, security, and operations. |
| `parser.py` | Cleans Markdown and retains heading context and positions. |
| `chunkers.py` | Fixed-size windows (400 characters, 50 overlap) or complete sections. |
| `metadata.py` | Adds source, chunk ID, section, strategy, and positions. |
| `compare_chunks.py` | Runs six chunk-quality checks and integrity checks. |
| `retriever.py` | Embeds source-file sections with MiniLM and performs cosine search. |
| `rag.py` | Uses local Ollama to select relevant source sentences and adds citations. |
| `test_*.py` | Tests parsing, file ingestion, index refresh, and citation validation. |
| `CLAUDE.md` | Assignment boundaries and coding rules. |
| `chunk_comparison.json` | Current chunking results. |
| `rag_evaluation.json` | Seven live RAG cases with retrieved evidence and answers. |
| `rag_baseline.json` | Historical run showing unsupported claims before the grounding fix. |
| Assignment PDFs | Supporting assignment/reflection documents; not RAG input. |

## Run

Use Python 3.10+ from the project root. Day 05 needs the standard library;
retrieval/RAG also need `numpy`, `sentence-transformers`, `ollama`, the embedding
model, and a running Ollama service with `llama3` installed.

```powershell
# Compare chunking strategies
python Day05-08/compare_chunks.py

# Ask RAG a question
python Day05-08/rag.py "How many vacation days do employees receive each year?"

# Run the seven assignment questions and save results
python Day05-08/rag.py --evaluate --output Day05-08/rag_evaluation.json

# Run automated tests
python -m unittest discover -s Day05-08 -p "test_*.py" -v
```

RAG options: `--model llama3`, `--top-k 3`. Every result includes retrieved
passages, scores, source filename, headings, document fingerprint, and citations.
Chunk IDs identify section positions in the current document version.

## Grounding & Verification

Ollama selects complete source sentences; the application renders those exact
sentences with their actual source IDs. This prevents unsupported paraphrases.
Missing evidence returns: "The available evidence does not provide enough information."
Selection can still omit relevant evidence, so inspect retrieval, answer, and
citations separately. A similarity score is not factual confidence.

The six chunk checks cover boundaries, headings, small details, overlap,
metadata, and mixed structures. With the updated sample, fixed-size produces
9 chunks and structural produces 11. Structural preserves whole sections;
fixed-size splits the long policy and table. All 32 regression tests pass.

`WARN` indicates a quality tradeoff; `SKIP` means a sample probe is absent.
The parser supports a Markdown subset, not PDF/Word input. No agents or MCP.

## Day 08: Evaluate and Improve

`day08_cases.json` defines 12 cases with expected evidence, missing-information
behavior, and prohibited claims. `evaluate_rag.py` runs the existing RAG and
checks retrieval, grounding, relevance, citations, and abstention separately.
Reports retain every passage and answer; no LLM judge is used.

```powershell
python Day05-08/evaluate_rag.py --variant baseline --output Day05-08/day08_baseline_rerun.json
python Day05-08/evaluate_rag.py --variant improved --output Day05-08/day08_improved_rerun.json
python Day05-08/evaluate_rag.py --compare Day05-08/day08_baseline_rerun.json Day05-08/day08_improved_rerun.json --output Day05-08/day08_comparison_rerun.json
```

The runs must use identical source, dataset, model, retrieval, and decoding
settings. Existing reports are protected; use another `--output` path or
`--force` to deliberately rerun. Inspect `day08_comparison.md` for the final
failure analysis, controlled change, and recommendation.

Results: baseline **9/12**, proposed partial-evidence policy **6/12**. The change
was rejected; baseline behavior remains the default. The candidate is available
only through `--variant improved` or `rag.py --partial-evidence` for inspection.
The word "improved" names the experimental variant, not a successful outcome.
