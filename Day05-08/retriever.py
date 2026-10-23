"""Day 06: embed structural chunks from sample_doc.md and search by cosine similarity.

The vector index lives in memory. Changed Markdown rebuilds the index on the next
search; no separate policy list or persisted vector database is maintained.
"""

from functools import lru_cache
from hashlib import sha256
from pathlib import Path

if __package__:
    from .parser import parse_markdown
    from .chunkers import structural_chunks
    from .metadata import enrich_chunks
else:
    from parser import parse_markdown
    from chunkers import structural_chunks
    from metadata import enrich_chunks


DOCUMENT_PATH = Path(__file__).resolve().with_name("sample_doc.md")
EMBEDDING_MODEL = "all-MiniLM-L6-v2"


def _parse_chunks(markdown, source_document):
    document = parse_markdown(markdown, source_document)
    records = enrich_chunks(structural_chunks(document), document.source_document)
    fingerprint = sha256(markdown.encode("utf-8")).hexdigest()
    for record in records:
        meta = record["metadata"]
        meta.update(section=meta["section_heading"], strategy=meta["chunk_strategy"],
                    source_sha256=fingerprint)
    return [{"id": r["metadata"]["chunk_index"], **r} for r in records]


def load_chunks(document_path=DOCUMENT_PATH):
    """Read the source file without loading the embedding model."""
    path = Path(document_path)
    return _parse_chunks(path.read_text(encoding="utf-8"), path.name)


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBEDDING_MODEL)


@lru_cache(maxsize=1)
def _index(source_path, markdown):
    chunks = _parse_chunks(markdown, Path(source_path).name)
    if not chunks:
        return chunks, None
    texts = [f"{c['metadata']['section']}\n{c['text']}" for c in chunks]
    vectors = _embedding_model().encode(texts, normalize_embeddings=True)
    return chunks, vectors


def search(query: str, top_k: int = 2, document_path=DOCUMENT_PATH):
    """Keep the Day 06 model and normalized-dot-product scoring.

    IDs identify section positions in this document version. Source name,
    heading, offsets, and fingerprint accompany each hit for traceability.
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("Query must not be empty")
    if type(top_k) is not int or top_k <= 0:
        raise ValueError("top_k must be a positive integer")
    path = Path(document_path).resolve()
    chunks, vectors = _index(str(path), path.read_text(encoding="utf-8"))
    if not chunks:
        return []
    import numpy as np
    query_vector = _embedding_model().encode([query], normalize_embeddings=True)[0]
    scores = np.dot(vectors, query_vector)
    top_indices = np.argsort(-scores, kind="stable")[:top_k]
    return [{"rank": rank, "chunk_id": chunks[idx]["id"], "score": float(scores[idx]),
             "text": chunks[idx]["text"], "metadata": dict(chunks[idx]["metadata"])}
            for rank, idx in enumerate(top_indices, 1)]


test_queries = [
    ("Semantic paraphrase", "How many vacation days do employees get each year?"),
    ("Approval rule", "I want to take five consecutive days off. Is manager approval required?"),
    ("Travel approval", "Who needs to approve an overseas business trip?"),
    ("Expense detail", "When are receipts required for travel expenses?"),
    ("Exact terminology", "Find the policy section about Sick Leave."),
    ("Unsupported", "What is the company's parental leave duration?"),
]


if __name__ == "__main__":
    print(f"Day 06 retrieval | Source: {DOCUMENT_PATH.name}")
    for title, query in test_queries:
        print(f"\n{title}: {query}")
        for hit in search(query):
            print(f"  Rank {hit['rank']} | Source ID: {hit['chunk_id']} | "
                  f"Score: {hit['score']:.4f} | {hit['metadata']['section']}")
            print(f"  {hit['text']}")
