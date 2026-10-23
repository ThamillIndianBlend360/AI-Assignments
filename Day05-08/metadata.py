"""Attach source identity and reconstructable section locations to chunks."""

from typing import Iterable

if __package__:
    from .chunkers import Chunk
else:
    from chunkers import Chunk


def enrich_chunks(chunks: Iterable[Chunk], source_document: str) -> list[dict]:
    records = []
    for index, chunk in enumerate(chunks):
        paths = [list(path) for path in chunk.heading_paths]
        records.append({
            "text": chunk.text,
            "metadata": {
                "source_document": source_document,
                "chunk_index": index,
                "section_heading": " > ".join(paths[0]) if paths and paths[0] else "Preamble",
                "chunk_strategy": chunk.strategy,
                "heading_paths": paths,
                "start_char": chunk.start,
                "end_char": chunk.end,
            },
        })
    return records
