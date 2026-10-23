"""Two deterministic chunking strategies over the same normalized document."""

from dataclasses import dataclass

if __package__:
    from .parser import ParsedDocument
else:
    from parser import ParsedDocument


@dataclass(frozen=True)
class Chunk:
    text: str
    start: int
    end: int
    heading_paths: tuple[tuple[str, ...], ...]
    strategy: str


def _contexts(document: ParsedDocument, start: int, end: int) -> tuple[tuple[str, ...], ...]:
    paths = []
    for block in document.blocks:
        if block.start < end and block.end > start and block.heading_path not in paths:
            paths.append(block.heading_path)
    return tuple(paths)


def fixed_size_chunks(document: ParsedDocument, chunk_size: int = 400,
                      overlap: int = 50) -> list[Chunk]:
    """Use exact character windows; the final window can be shorter.

    Preserve whitespace in windows so overlap and coverage are measurable.
    All intersecting heading paths are retained when a window crosses sections.
    """
    if not isinstance(chunk_size, int) or isinstance(chunk_size, bool) or chunk_size <= 0:
        raise ValueError("chunk_size must be a positive integer")
    if not isinstance(overlap, int) or isinstance(overlap, bool) or not 0 <= overlap < chunk_size:
        raise ValueError("overlap must be an integer satisfying 0 <= overlap < chunk_size")
    chunks = []
    start = 0
    while start < len(document.text):
        end = min(start + chunk_size, len(document.text))
        chunks.append(Chunk(document.text[start:end], start, end,
                            _contexts(document, start, end), "fixed_size"))
        if end == len(document.text):
            break
        start += chunk_size - overlap
    return chunks


def structural_chunks(document: ParsedDocument) -> list[Chunk]:
    """Keep each heading's direct body together, including whole lists/tables.

    No character cap is applied: long sections are reported by the evaluator.
    A child heading starts a new section and retains its full parent path.
    """
    chunks = []
    start = end = None
    section_id = None
    for block in document.blocks:
        if section_id is not None and block.section_id != section_id:
            chunks.append(Chunk(document.text[start:end], start, end,
                                _contexts(document, start, end), "structural"))
            start = None
        if start is None:
            start = block.start
        end = block.end
        section_id = block.section_id
    if start is not None:
        chunks.append(Chunk(document.text[start:end], start, end,
                            _contexts(document, start, end), "structural"))
    return chunks
