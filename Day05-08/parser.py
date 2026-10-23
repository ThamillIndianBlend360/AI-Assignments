"""Normalize a local Markdown document while preserving its heading context.

Supported input: ATX headings, paragraphs, lists, pipe tables, blockquotes,
inline formatting, links, HTML comments, and fenced code. This is deliberately
a small Markdown subset, not a general-purpose Markdown renderer.
"""

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class TextBlock:
    text: str
    kind: str
    heading_path: tuple[str, ...]
    section_id: int
    start: int
    end: int


@dataclass(frozen=True)
class ParsedDocument:
    source_document: str
    text: str
    blocks: tuple[TextBlock, ...]


def clean_inline(text: str) -> str:
    """Remove presentation syntax, keeping link labels and code identifiers."""
    text = re.sub(r"!?\[([^\]]*)\]\([^\n)]*\)", r"\1", text)
    text = re.sub(r"`+([^`]+)`+", r"\1", text)
    for marker in ("**", "__", "~~", "*", "_"):
        escaped = re.escape(marker)
        text = re.sub(
            rf"(?<!\w){escaped}(?=\S)(.+?)(?<=\S){escaped}(?!\w)",
            r"\1", text,
        )
    return re.sub(r"[ \t]+", " ", text).strip()


def parse_markdown(markdown: str, source_document: str = "<memory>") -> ParsedDocument:
    """Return normalized body text and blocks with offsets into that same text.

    Headings live in block context instead of the body. Paragraph line wraps
    become spaces; list items, table rows, and code lines remain distinct.
    """
    markdown = markdown.replace("\r\n", "\n").replace("\r", "\n").lstrip("\ufeff")
    headings: list[tuple[int, str]] = []
    section_id = 0
    pending: list[str] = []
    kind = "paragraph"
    blocks: list[TextBlock] = []
    pieces: list[str] = []
    offset = 0
    fence: str | None = None
    in_comment = False

    def flush() -> None:
        nonlocal offset
        if not pending:
            return
        body = (" " if kind == "paragraph" else "\n").join(pending).strip("\n")
        pending.clear()
        if not body.strip():
            return
        if pieces:
            offset += 2
        blocks.append(TextBlock(body, kind, tuple(h[1] for h in headings),
                                section_id, offset, offset + len(body)))
        pieces.append(body)
        offset += len(body)

    for raw in markdown.split("\n"):
        stripped = raw.strip()
        if fence is not None:
            if re.fullmatch(re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", stripped):
                flush()
                fence = None
            else:
                pending.append(raw.rstrip())
            continue

        # Strip comments outside code, including comments spanning lines.
        visible = ""
        rest = raw
        while rest:
            if in_comment:
                end = rest.find("-->")
                if end < 0:
                    rest = ""
                else:
                    rest = rest[end + 3:]
                    in_comment = False
            else:
                start = rest.find("<!--")
                if start < 0:
                    visible += rest
                    rest = ""
                else:
                    visible += rest[:start]
                    rest = rest[start + 4:]
                    in_comment = True
        stripped = visible.strip()
        opening = re.match(r"^(`{3,}|~{3,})(.*)$", stripped)
        if opening:
            flush()
            fence = opening.group(1)
            kind = "code"
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if heading:
            flush()
            level = len(heading.group(1))
            title = clean_inline(re.sub(r"\s+#+\s*$", "", heading.group(2)))
            while headings and headings[-1][0] >= level:
                headings.pop()
            headings.append((level, title))
            section_id += 1
            continue
        if not stripped or re.fullmatch(r"(?:\*\s*){3,}|(?:-\s*){3,}|(?:_\s*){3,}", stripped):
            flush()
            continue
        # A pipe-table delimiter carries layout, not a data row.
        if "|" in stripped and re.fullmatch(r"\|?\s*:?-{3,}:?\s*(?:\|\s*:?-{3,}:?\s*)+\|?", stripped):
            continue
        stripped = re.sub(r"^(?:>\s*)+", "", stripped)
        new_kind = ("list" if re.match(r"^(?:[-+*]|\d+[.)])\s+", stripped)
                    else "table" if "|" in stripped else "paragraph")
        if pending and new_kind != kind:
            flush()
        kind = new_kind
        pending.append(clean_inline(stripped))
    flush()
    return ParsedDocument(source_document, "\n\n".join(pieces), tuple(blocks))


def load_document(path: str | Path) -> ParsedDocument:
    path = Path(path)
    return parse_markdown(path.read_text(encoding="utf-8"), path.name)
